#!/usr/bin/env python3
# scan_lk.py — Jz8root (https://github.com/Jz8Root/xiaomi-mtk-bootloader-unlock)
# Original research: XDA thread https://xdaforums.com/t/4784527/
# License: AGPL-3.0
"""
scan_lk.py — LK Binary Scanner for MediaTek Bootloader Unlock

Analyzes a Xiaomi MediaTek LK (Little Kernel) binary to determine if the device
uses the RPMB lock mechanism introduced in HyperOS/MIUI14+ and whether it is
compatible with the RPMB erase + seccfg unlock method.

Usage:
    python3 scan_lk.py <lk_binary_path> [--json]

Output:
    Analysis report including:
    - Presence of the RPMB magic string
    - RPMB type (UFS Samsung 0x400000 or 0x1000000)
    - Xiaomi RSA-2048 public key detection
    - Key function signatures
    - Compatibility verdict (0-100%)
"""

import sys
import struct
import json
import hashlib
from pathlib import Path
from typing import Optional

# ═══════════════════════════════════════════════════════════
# KNOWN SIGNATURES & PATTERNS
# ═══════════════════════════════════════════════════════════

# RPMB magic string hardcoded in Xiaomi LK bootloader binaries (HyperOS/MIUI14+).
# Found at offset 0x110608 in lk_a.img from fleur HyperOS OS1.0.11.0.TKEEUXM.
# Verify: xxd -s 0x110608 -l 8 lk_a.img → "Jz8PNRUF"
# The author's handle (Jz8root) derives from this firmware constant discovered
# during reverse engineering — not the other way around.
RPMB_MAGIC = b"Jz8PNRUF"

# Known RPMB UFS type identifiers
RPMB_TYPE_SAMSUNG = 0x400000    # UFS Samsung type
RPMB_TYPE_ALT     = 0x1000000   # Alternative UFS type

# RPMB offsets — LK-internal addressing (passed to rpmb_read()).
# WARNING: These are NOT byte offsets in the mtkclient RPMB dump.
# The mapping to dump offsets depends on the RPMB driver and UFS type.
# For fleur (Samsung UFS): LK offset 0x3FE0 maps to dump offset 0xE00000 (sector 57344).
# See proof/VERIFICATION.md for the proven sector math.
RPMB_OFFSETS_SAMSUNG = {
    "magic":           0x3FE0,     # LK-internal, maps to dump sector 57344
    "lock_state_len":  0x40E0,     # LK-internal, maps to dump sector 57600
    "signature_data":  0x41E0,     # LK-internal, maps to dump sector 57856
}

# RPMB offsets for alternative type (0x1000000)
RPMB_OFFSETS_ALT = {
    "magic":           0xE000,
    "lock_state_len":  0xE100,
    "signature_data":  0xE200,
}

# RSA-2048 modulus first 16 bytes — extracted from fleur LK at offset 0x1109B8.
# Used as heuristic to detect the same Xiaomi signing key in other LK binaries.
# If the prefix matches, it's very likely the same key. If not, the fallback
# uses entropy analysis to find any RSA-2048 key (less precise, marked as such).
RSA_MODULUS_PREFIX = bytes([
    0xB7, 0xFB, 0xCD, 0xE3, 0x20, 0xB8, 0x27, 0xE3,
    0x4F, 0x0D, 0x13, 0xC4, 0x0E, 0xC5, 0xC8, 0xAB,
])

# RSA exponent 65537 in bytes (big-endian)
RSA_EXPONENT = bytes([0x01, 0x00, 0x01])

# Function detection via string reference search.
# NOTE: This is NOT ARM instruction pattern matching — it searches for ASCII
# string references (debug names, log messages) that indicate the presence of
# known functions. Stripped binaries without debug strings will return no hits.
FUNCTION_SIGNATURES = {
    "mi_check_magic": {
        # Pattern: reads 8 bytes and compares with "Jz8PNRUF"
        "string_refs": [b"Jz8PNRUF"],
        "description": "Checks RPMB magic — returns 0 (present) or 3 (absent)",
    },
    "mi_get_lock_state": {
        # References mi_check_magic result
        "string_refs": [b"mi_get_lock_state"],
        "description": "Reads RPMB lock state — overrides seccfg when magic present",
    },
    "get_lock_state": {
        # Main lock state function
        "string_refs": [b"get_lock_state", b"lock_state"],
        "description": "Main lock state function — reads seccfg + RPMB",
    },
    "seccfg_set_lock_state": {
        "string_refs": [b"seccfg", b"lock_state"],
        "description": "Writes lock state to seccfg partition",
    },
    "rpmb_read": {
        "string_refs": [b"rpmb_read", b"rpmb read"],
        "description": "Reads N bytes from RPMB",
    },
    "rpmb_write": {
        "string_refs": [b"rpmb_write", b"rpmb write"],
        "description": "Writes N bytes to RPMB",
    },
    "fastboot_oem_lks": {
        "string_refs": [b"oem lks", b"oem setmtklks", b"oem chkmtklks"],
        "description": "Hidden fastboot OEM lock state commands",
    },
    "verify_unlock_sig": {
        "string_refs": [b"verify", b"unlock", b"signature"],
        "description": "RSA signature verification for unlock token",
    },
}

# seccfg version identifiers
SECCFG_VERSIONS = {
    b"SECCFG_V3": "V3",
    b"SECCFG_V4": "V4",
    b"SEC_CFG": "generic",
    b"seccfg": "generic",
}

# Lock state constants found in LK binaries
LOCK_STATE_CONSTANTS = {
    1: "DEFAULT (RPMB not initialized, fallback to seccfg)",
    3: "UNLOCK",
    4: "LOCK",
}


def scan_binary(data: bytes) -> dict:
    """
    Full analysis of an LK binary.
    Returns a structured dictionary with all results.
    """
    result = {
        "file_size": len(data),
        "file_md5": hashlib.md5(data).hexdigest(),
        "file_sha256": hashlib.sha256(data).hexdigest(),
        "magic": scan_magic(data),
        "rpmb": scan_rpmb_type(data),
        "rsa_key": scan_rsa_key(data),
        "seccfg": scan_seccfg(data),
        "functions": scan_functions(data),
        "strings": scan_relevant_strings(data),
        "fastboot_commands": scan_fastboot_commands(data),
        "verdict": None,
    }

    # Generate verdict
    result["verdict"] = generate_verdict(result)

    return result


def scan_magic(data: bytes) -> dict:
    """Searches for the RPMB magic 'Jz8PNRUF' in the binary."""
    occurrences = []
    offset = 0
    while True:
        pos = data.find(RPMB_MAGIC, offset)
        if pos == -1:
            break
        # Get surrounding context (32 bytes before and after)
        ctx_start = max(0, pos - 32)
        ctx_end = min(len(data), pos + len(RPMB_MAGIC) + 32)
        context_hex = data[ctx_start:ctx_end].hex()

        occurrences.append({
            "offset": pos,
            "offset_hex": f"0x{pos:08X}",
            "context_hex": context_hex,
        })
        offset = pos + 1

    return {
        "found": len(occurrences) > 0,
        "count": len(occurrences),
        "occurrences": occurrences,
        "magic_string": RPMB_MAGIC.decode('ascii'),
    }


def scan_rpmb_type(data: bytes) -> dict:
    """Detects the RPMB type used (0x400000 or 0x1000000)."""
    types_found = []

    # Search for RPMB type constants
    # In ARM Thumb, constants are often loaded via LDR from literal pool
    for rpmb_type, name in [(RPMB_TYPE_SAMSUNG, "UFS_Samsung_0x400000"), (RPMB_TYPE_ALT, "UFS_Alt_0x1000000")]:
        # Search as 32-bit little-endian value
        type_bytes = struct.pack('<I', rpmb_type)
        offset = 0
        while True:
            pos = data.find(type_bytes, offset)
            if pos == -1:
                break
            types_found.append({
                "type": name,
                "value": f"0x{rpmb_type:X}",
                "offset": pos,
                "offset_hex": f"0x{pos:08X}",
            })
            offset = pos + 1

    # Determine primary type
    primary_type = None
    offsets = None
    if any(t["type"] == "UFS_Samsung_0x400000" for t in types_found):
        primary_type = "UFS_Samsung_0x400000"
        offsets = {k: f"0x{v:04X}" for k, v in RPMB_OFFSETS_SAMSUNG.items()}
    elif any(t["type"] == "UFS_Alt_0x1000000" for t in types_found):
        primary_type = "UFS_Alt_0x1000000"
        offsets = {k: f"0x{v:04X}" for k, v in RPMB_OFFSETS_ALT.items()}

    return {
        "types_found": types_found,
        "primary_type": primary_type,
        "rpmb_offsets": offsets,
        "magic_sector": 57344 if primary_type == "UFS_Samsung_0x400000" else (0xE000 // 0x100 if primary_type else None),
    }


def scan_rsa_key(data: bytes) -> dict:
    """Searches for the Xiaomi RSA-2048 public key."""
    results = {
        "modulus_found": False,
        "exponent_found": False,
        "modulus_offset": None,
        "exponent_offset": None,
        "key_size_bits": None,
    }

    # Search for RSA modulus prefix
    pos = data.find(RSA_MODULUS_PREFIX)
    if pos != -1:
        results["modulus_found"] = True
        results["modulus_offset"] = pos
        results["modulus_offset_hex"] = f"0x{pos:08X}"
        results["key_size_bits"] = 2048
        # Extract full 256-byte modulus
        if pos + 256 <= len(data):
            modulus = data[pos:pos + 256]
            results["modulus_hex_preview"] = modulus[:32].hex()
            results["modulus_md5"] = hashlib.md5(modulus).hexdigest()

    # Search for RSA exponent 65537 near modulus
    if results["modulus_found"]:
        # Look within 1KB before the modulus for exponent
        search_start = max(0, pos - 1024)
        search_end = min(len(data), pos + 512)
        search_area = data[search_start:search_end]
        exp_pos = search_area.find(RSA_EXPONENT)
        if exp_pos != -1:
            results["exponent_found"] = True
            results["exponent_offset"] = search_start + exp_pos
            results["exponent_offset_hex"] = f"0x{(search_start + exp_pos):08X}"
            results["exponent_value"] = 65537
    else:
        # Try broader search for any RSA-2048 modulus (256 bytes of high entropy)
        # Look for the exponent pattern near high-entropy blocks
        exp_offset = 0
        while True:
            exp_pos = data.find(RSA_EXPONENT, exp_offset)
            if exp_pos == -1:
                break
            # Check if this looks like it's part of an RSA key structure
            # Exponent is typically near the end of key structure
            if exp_pos > 256:
                # Check preceding 256 bytes for high entropy (likely modulus)
                candidate = data[exp_pos - 260:exp_pos - 4]
                if len(candidate) == 256:
                    # Simple entropy check: count unique bytes
                    unique = len(set(candidate))
                    if unique > 200:  # High entropy = likely RSA modulus
                        results["exponent_found"] = True
                        results["exponent_offset"] = exp_pos
                        results["exponent_offset_hex"] = f"0x{exp_pos:08X}"
                        results["exponent_value"] = 65537
                        results["modulus_found"] = True
                        results["modulus_offset"] = exp_pos - 260
                        results["modulus_offset_hex"] = f"0x{(exp_pos - 260):08X}"
                        results["key_size_bits"] = 2048
                        results["modulus_hex_preview"] = candidate[:32].hex()
                        results["note"] = "RSA key detected via entropy heuristic (not exact fleur modulus match — may be a different Xiaomi key or unrelated RSA key)"
                        break
            exp_offset = exp_pos + 1

    return results


def scan_seccfg(data: bytes) -> dict:
    """Detects the seccfg version and references."""
    results = {
        "version": None,
        "references": [],
    }

    for pattern, version in SECCFG_VERSIONS.items():
        offset = 0
        while True:
            pos = data.find(pattern, offset)
            if pos == -1:
                break
            results["references"].append({
                "pattern": pattern.decode('ascii', errors='replace'),
                "version": version,
                "offset": pos,
                "offset_hex": f"0x{pos:08X}",
            })
            if results["version"] is None or version.startswith("V"):
                results["version"] = version
            offset = pos + 1

    return results


def scan_functions(data: bytes) -> dict:
    """Searches for known function string references in the binary."""
    found = {}

    for func_name, sig_info in FUNCTION_SIGNATURES.items():
        refs = []
        for pattern in sig_info["string_refs"]:
            offset = 0
            while True:
                pos = data.find(pattern, offset)
                if pos == -1:
                    break
                refs.append({
                    "pattern": pattern.decode('ascii', errors='replace'),
                    "offset": pos,
                    "offset_hex": f"0x{pos:08X}",
                })
                offset = pos + 1

        if refs:
            found[func_name] = {
                "description": sig_info["description"],
                "references": refs,
                "count": len(refs),
            }

    return {
        "detected": list(found.keys()),
        "total": len(found),
        "details": found,
    }


def scan_relevant_strings(data: bytes) -> dict:
    """Extracts relevant strings from the binary."""
    relevant_patterns = [
        b"lock_state",
        b"unlock",
        b"LOCK",
        b"UNLOCK",
        b"rpmb",
        b"RPMB",
        b"seccfg",
        b"fastboot",
        b"oem ",
        b"Kamakiri",
        b"brom",
        b"BROM",
        b"preloader",
        b"mi_",
        b"xiaomi",
        b"Xiaomi",
        b"flashing",
        b"bootloader",
    ]

    found_strings = {}
    for pattern in relevant_patterns:
        key = pattern.decode('ascii', errors='replace')
        offset = 0
        locations = []
        while True:
            pos = data.find(pattern, offset)
            if pos == -1:
                break
            # Extract surrounding null-terminated string
            str_start = pos
            while str_start > 0 and data[str_start - 1] >= 0x20 and data[str_start - 1] < 0x7F:
                str_start -= 1
            str_end = pos + len(pattern)
            while str_end < len(data) and data[str_end] >= 0x20 and data[str_end] < 0x7F:
                str_end += 1
            full_str = data[str_start:str_end].decode('ascii', errors='replace')

            if len(full_str) > 2 and full_str not in [s["string"] for s in locations]:
                locations.append({
                    "string": full_str[:128],  # Limit length
                    "offset": pos,
                    "offset_hex": f"0x{pos:08X}",
                })
            offset = pos + 1
            if len(locations) >= 10:  # Max 10 per pattern
                break

        if locations:
            found_strings[key] = locations

    return {
        "total_patterns": len(found_strings),
        "details": found_strings,
    }


def scan_fastboot_commands(data: bytes) -> dict:
    """Searches for hidden fastboot OEM commands."""
    commands_to_find = [
        b"oem lks",
        b"oem setmtklks",
        b"oem chkmtklks",
        b"flashing get_unlock_ability",
        b"flashing unlock",
        b"flashing lock",
        b"oem unlock",
        b"oem lock",
        b"oem device-info",
    ]

    found = []
    for cmd in commands_to_find:
        pos = data.find(cmd)
        if pos != -1:
            found.append({
                "command": cmd.decode('ascii'),
                "offset": pos,
                "offset_hex": f"0x{pos:08X}",
            })

    return {
        "total": len(found),
        "commands": found,
    }


def generate_verdict(result: dict) -> dict:
    """
    Generates a compatibility verdict based on scan results.
    """
    magic = result["magic"]
    rpmb = result["rpmb"]
    rsa = result["rsa_key"]
    seccfg = result["seccfg"]
    functions = result["functions"]

    score = 0
    max_score = 100
    details = []
    blockers = []

    # 1. Magic "Jz8PNRUF" present (40 points — critical)
    if magic["found"]:
        score += 40
        details.append({
            "check": "Magic Jz8PNRUF",
            "status": "FOUND",
            "points": 40,
            "note": f"Found {magic['count']} time(s). This device uses the Xiaomi RPMB lock mechanism.",
        })
    else:
        details.append({
            "check": "Magic Jz8PNRUF",
            "status": "NOT_FOUND",
            "points": 0,
            "note": "Magic not found. Either MIUI13 or older (seccfg alone works), or different mechanism.",
        })

    # 2. RPMB type detected (15 points)
    if rpmb["primary_type"]:
        score += 15
        details.append({
            "check": "RPMB Type",
            "status": "DETECTED",
            "points": 15,
            "note": f"Type: {rpmb['primary_type']}. RPMB offsets identified.",
        })
    else:
        details.append({
            "check": "RPMB Type",
            "status": "NOT_FOUND",
            "points": 0,
            "note": "RPMB type not identified.",
        })

    # 3. RSA key found (15 points)
    if rsa["modulus_found"]:
        score += 15
        details.append({
            "check": "RSA-2048 Key",
            "status": "FOUND",
            "points": 15,
            "note": f"RSA {rsa.get('key_size_bits', '?')}-bit public key found. Signature verification active.",
        })
    else:
        score += 5  # partial: might just be different key format
        details.append({
            "check": "RSA-2048 Key",
            "status": "NOT_FOUND",
            "points": 5,
            "note": "RSA key not found (may be different format or no signature verification).",
        })

    # 4. seccfg detected (15 points)
    if seccfg["version"]:
        score += 15
        details.append({
            "check": "seccfg",
            "status": "DETECTED",
            "points": 15,
            "note": f"Version: {seccfg['version']}. seccfg support confirmed.",
        })
    else:
        details.append({
            "check": "seccfg",
            "status": "NOT_FOUND",
            "points": 0,
            "note": "seccfg not detected.",
        })
        blockers.append("seccfg not detected")

    # 5. Key functions detected (15 points)
    key_funcs = ["mi_check_magic", "fastboot_oem_lks"]
    funcs_found = sum(1 for f in key_funcs if f in functions["detected"])
    func_score = int(15 * (funcs_found / len(key_funcs)))
    score += func_score
    details.append({
        "check": "Key Functions",
        "status": "PARTIAL" if funcs_found > 0 else "NOT_FOUND",
        "points": func_score,
        "note": f"{functions['total']} function references found: {', '.join(functions['detected'][:5])}",
    })

    # Generate overall verdict
    if score >= 70 and magic["found"]:
        compatibility = "COMPATIBLE"
        method = "RPMB erase (sector {}) + seccfg unlock".format(
            rpmb.get("magic_sector", "57344")
        )
        message = "This device is compatible with the RPMB erase + seccfg unlock method."
    elif score >= 40 and not magic["found"] and seccfg["version"]:
        compatibility = "COMPATIBLE_SECCFG_ONLY"
        method = "seccfg unlock only (no RPMB lock)"
        message = "RPMB magic not found. seccfg alone should work (MIUI13 or older)."
    elif score >= 30:
        compatibility = "MAYBE"
        method = "Further analysis needed"
        message = "Some indicators present but analysis incomplete. Scan the full LK binary."
    else:
        compatibility = "UNKNOWN"
        method = "Undetermined"
        message = "Not enough indicators. Verify the file is a valid MediaTek LK binary."

    return {
        "compatibility": compatibility,
        "score": score,
        "max_score": max_score,
        "percentage": round(score / max_score * 100),
        "method": method,
        "message": message,
        "details": details,
        "blockers": blockers,
    }


def format_report(result: dict) -> str:
    """Formats the report as human-readable text."""
    lines = []
    lines.append("══════════════════════════════════════════════════════════")
    lines.append("  LK BINARY SCAN REPORT — MTKClient Unlock Analyzer")
    lines.append("══════════════════════════════════════════════════════════")
    lines.append("")
    lines.append(f"  File size  : {result['file_size']:,} bytes ({result['file_size'] / 1024 / 1024:.1f} MB)")
    lines.append(f"  MD5        : {result['file_md5']}")
    lines.append(f"  SHA256     : {result['file_sha256'][:32]}...")
    lines.append("")

    # Verdict
    v = result["verdict"]
    lines.append(f"  ┌─────────────────────────────────────────┐")
    lines.append(f"  │  VERDICT: {v['compatibility']:<31}│")
    lines.append(f"  │  Score  : {v['score']}/{v['max_score']} ({v['percentage']}%){' ' * (26 - len(str(v['percentage'])))}│")
    lines.append(f"  │  Method: {v['method'][:31]:<31}│")
    lines.append(f"  └─────────────────────────────────────────┘")
    lines.append("")

    # Magic
    m = result["magic"]
    status = "✓ FOUND" if m["found"] else "✗ ABSENT"
    lines.append(f"  [MAGIC] Jz8PNRUF : {status}")
    if m["found"]:
        for occ in m["occurrences"]:
            lines.append(f"    @ {occ['offset_hex']}")
    lines.append("")

    # RPMB
    r = result["rpmb"]
    lines.append(f"  [RPMB] Type : {r['primary_type'] or 'Not detected'}")
    if r["rpmb_offsets"]:
        for k, v_val in r["rpmb_offsets"].items():
            lines.append(f"    {k:20s} : {v_val}")
    lines.append("")

    # RSA
    rsa = result["rsa_key"]
    lines.append(f"  [RSA]  Modulus : {'✓ FOUND' if rsa['modulus_found'] else '✗ NOT FOUND'}")
    if rsa["modulus_found"]:
        lines.append(f"    @ {rsa.get('modulus_offset_hex', '?')}")
        lines.append(f"    Key size: {rsa.get('key_size_bits', '?')} bits")
    lines.append("")

    # seccfg
    s = result["seccfg"]
    lines.append(f"  [SECCFG] Version : {s['version'] or 'Not detected'}")
    lines.append("")

    # Functions
    f = result["functions"]
    lines.append(f"  [FUNCTIONS] {f['total']} detected:")
    for name in f["detected"]:
        desc = f["details"][name]["description"]
        lines.append(f"    ✓ {name}: {desc}")
    lines.append("")

    # Fastboot
    fb = result["fastboot_commands"]
    lines.append(f"  [FASTBOOT] {fb['total']} OEM commands:")
    for cmd in fb["commands"]:
        lines.append(f"    ✓ {cmd['command']} @ {cmd['offset_hex']}")
    lines.append("")

    lines.append("══════════════════════════════════════════════════════════")
    lines.append(f"  {v['message']}")
    lines.append("══════════════════════════════════════════════════════════")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scan_lk.py <lk_binary_path> [--json]")
        print("")
        print("Analyzes a MediaTek LK binary for bootloader unlock compatibility.")
        print("")
        print("How to get the LK binary:")
        print("  # From stock firmware:")
        print("  unzip firmware.zip")
        print("  # -> images/lk.img or lk_a.img")
        print("")
        print("  # From device via mtkclient:")
        print("  python3 mtk.py da r lk_a lk_a.bin")
        sys.exit(1)

    filepath = sys.argv[1]
    json_output = "--json" in sys.argv

    MAX_FILE_SIZE = 256 * 1024 * 1024  # 256 MB — no LK binary should be larger

    if not Path(filepath).exists():
        print(f"[ERROR] File not found: {filepath}")
        sys.exit(1)

    file_size = Path(filepath).stat().st_size
    if file_size > MAX_FILE_SIZE:
        print(f"[ERROR] File too large ({file_size:,} bytes, max {MAX_FILE_SIZE:,}). Are you sure this is an LK binary?")
        sys.exit(1)

    print(f"[*] Reading {filepath}...")
    with open(filepath, "rb") as f:
        data = f.read()

    print(f"[*] Size: {len(data):,} bytes")
    print(f"[*] Scanning...")

    result = scan_binary(data)

    if json_output:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(format_report(result))


if __name__ == "__main__":
    main()
