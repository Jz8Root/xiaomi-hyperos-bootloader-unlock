# Xiaomi MTK Bootloader Unlock — HyperOS/MIUI14+ RPMB Bypass

**Tested on:** POCO M4 Pro 4G (fleur, MT6781) | **Status:** Phase 3 — Full method released  
**XDA Thread:** [xdaforums.com/t/4784527](https://xdaforums.com/t/4784527/)  
**Author:** [Jz8root](https://github.com/Jz8Root)

---

## The Problem

Since MIUI 14.0.3+ and HyperOS, `mtkclient da seccfg unlock` succeeds without errors — but the bootloader remains locked after reboot. This has been reported and left unsolved for 2+ years:

- [mtkclient #81](https://github.com/bkerler/mtkclient/issues/81) — Redmi 9A/9C (MT6762G) — open since 2021
- [mtkclient #764](https://github.com/bkerler/mtkclient/issues/764) — Redmi 10 5G (MT6833)
- [mtkclient #1405](https://github.com/bkerler/mtkclient/issues/1405) — MT6762G devices
- [mtkclient #1219](https://github.com/bkerler/mtkclient/issues/1219) — Redmi Note 8 Pro (MT6785)

## Root Cause

After reverse engineering the Little Kernel (LK) bootloader from HyperOS using Ghidra, I found that Xiaomi introduced a **dual-layer lock verification**:

```
get_lock_state():
  1. seccfg_state = read_seccfg()           <-- FALLBACK (what mtkclient writes)
  2. rpmb_state   = mi_get_lock_state()     <-- PRIORITY (overrides seccfg!)

  if rpmb_state == 1 (DEFAULT / no magic):
      return seccfg_state    <-- seccfg decides
  else:
      return rpmb_state      <-- RPMB OVERRIDES seccfg
```

Starting with HyperOS, Xiaomi stores a magic string in the **RPMB** (Replay Protected Memory Block). When present, RPMB overrides seccfg — even if seccfg says UNLOCK, RPMB says LOCKED and wins.

**The fix:** erase the RPMB magic. This forces the LK to fall back to seccfg, which mtkclient can freely write to UNLOCK.

**Why it persists across reboots:** when the magic is absent AND seccfg = UNLOCK, the LK does NOT rewrite the magic. The code path that restores the magic only triggers when seccfg != UNLOCK. This behavior is inferred from the Ghidra decompilation of `mi_get_lock_state()` and confirmed empirically: RPMB dumps taken after multiple reboots show the magic region remains zeroed. See [proof/VERIFICATION.md](proof/VERIFICATION.md) for dump evidence.

| Lock State Value | Meaning |
|-----------------|---------|
| 1 | DEFAULT (RPMB not initialized, fallback to seccfg) |
| 3 | UNLOCKED |
| 4 | LOCKED |

## The Method — 3 Commands

### Prerequisites

- [mtkclient](https://github.com/bkerler/mtkclient) with Kamakiri BROM exploit
- Access to BROM mode (usually Vol+/Vol- while plugging USB — varies by device)
- Quality USB DATA cable (not charge-only)
- **MANDATORY:** Full backup of NV partitions (nvdata, nvcfg, nvram, persist, protect1, protect2)

### For HyperOS / MIUI 14+ Devices

```bash
cd mtkclient

# STEP 1: BACKUP RPMB — DO NOT SKIP THIS
python mtk.py da rpmb r rpmb_backup.bin

# STEP 2: Erase RPMB lock region
python mtk.py da rpmb e --sector 57344 --sectors 4

# STEP 3: Unlock seccfg
python mtk.py da seccfg unlock
```

**Between each command: unplug the phone, replug in BROM mode (Vol+/Vol-).**

If your device needs a specific preloader:
```bash
python mtk.py --preloader preloader_CODENAME.bin da rpmb r rpmb_backup.bin
python mtk.py --preloader preloader_CODENAME.bin da rpmb e --sector 57344 --sectors 4
python mtk.py --preloader preloader_CODENAME.bin da seccfg unlock
```

**Note on Step 2:** We erase only 4 sectors starting at 57344 — this targets only the magic region. The lock state length (sector 57600) and signature data (sector 57856) remain untouched. Erasing only the magic is sufficient: absent magic forces the DEFAULT->seccfg fallback path.

### Verification

```bash
fastboot oem lks          # Expected: lks = 0
fastboot getvar unlocked  # Expected: unlocked: yes
```

Open padlock logo on boot = success.

### For MIUI 11/12/13 (older firmware — no RPMB lock)

```bash
python mtk.py da seccfg unlock
```

One command. The RPMB mechanism doesn't exist on older firmware.

### Which Method Do I Need?

| Firmware | RPMB lock present | Method |
|----------|-------------------|--------|
| HyperOS 1 (2024, OS1.0.x) | YES — tested | RPMB erase + seccfg unlock |
| HyperOS 2/3 (2025-2026) | UNKNOWN — not tested | Use with caution, report results |
| MIUI 14 (2023) | Varies | Check your LK binary with scan_lk.py |
| MIUI 13 (2022) | NO | seccfg only |
| MIUI 11/12 (2021) | NO | seccfg only |

## RPMB Sector Reference

### Proven: POCO M4 Pro 4G (fleur, Samsung UFS)

Verified by RPMB dump analysis. See [proof/VERIFICATION.md](proof/VERIFICATION.md) for full evidence.

| Data | Dump Byte Offset | mtkclient Sector |
|------|-----------------|-----------------|
| Lock magic | **0xE00000** | **57344** |
| Lock state length | 0xE10000 | 57600 |
| Signature data | 0xE20000 | 57856 |

Sector math: `byte_offset / 256 = sector` → `0xE00000 / 0x100 = 57344`

Command: `da rpmb e --sector 57344 --sectors 4`

> **Note:** The LK code internally uses offset 0x3FE0 when calling `rpmb_read()`. The mapping
> from this LK-internal address to the physical dump offset 0xE00000 is handled by the RPMB
> driver and depends on the UFS type. For users, only the mtkclient sector number matters.

### Other UFS types (unverified)

Devices with different UFS RPMB configurations may use different sector numbers. If your
device doesn't match sector 57344, dump your RPMB first (`da rpmb r rpmb_dump.bin`), then
search for the magic string: `grep -boa "Jz8PNRUF" rpmb_dump.bin` to find the correct offset.
Convert to sector: `byte_offset / 256 = sector`.

## scan_lk.py — Compatibility Scanner

Analyzes any Xiaomi MTK LK binary using string searches and byte pattern matching:
- Whether the RPMB magic string is present in the binary (exact match)
- UFS RPMB type detection (heuristic based on constant values)
- RSA key detection (exact prefix match for known Xiaomi key, entropy heuristic fallback)
- Function presence detection via string references (NOT ARM instruction analysis — requires unstripped debug strings)
- Compatibility verdict with score (0-100%)

```bash
# From firmware ZIP
unzip firmware.zip  # -> images/lk.img or lk_a.img

# From device via mtkclient
python mtk.py da r lk_a lk_a.bin

# Run scanner
python3 scan_lk.py lk.img
python3 scan_lk.py lk.img --json  # structured output
```

See [COMPATIBILITY.md](COMPATIBILITY.md) for the full device database.

## FAQ

**Q: How can you erase RPMB without the device-specific RPMB key?**  
A: mtkclient derives the RPMB authentication key via the HACC engine through SEJ after the Kamakiri BROM exploit — the same mechanism it uses to handle SecCfgV4 encryption. The key derivation happens transparently when you run the `da rpmb e` command.

**Q: Will this wipe my data?**  
A: Yes. Unlocking the bootloader triggers a factory reset on first boot. Back up everything.

**Q: Can I relock after?**  
A: Yes. `mtk da seccfg lock` relocks. Full lock/unlock cycle tested and reversible.

**Q: Why erase only 4 sectors?**  
A: We only need to remove the magic string. The lock state length and signature data at higher sectors are irrelevant once the magic is absent — the LK falls back to seccfg without reading them.

## Warnings

1. **BACKUP RPMB FIRST.** Step 1 is your safety net. Never skip it.
2. **BACKUP NV PARTITIONS** (nvdata, nvcfg, nvram, persist, protect1, protect2) — without these, you risk "NV data corrupted" which breaks IMEI and baseband.
3. **THIS WILL WIPE YOUR DATA.** Factory reset on first boot after unlock.
4. **BROM V6 = NO GO.** If your SoC is MT6789 or newer, Kamakiri is patched in hardware.
5. **HyperOS 1 ONLY (tested).** HyperOS 2/3 have NOT been verified.
6. Unlocking the bootloader voids manufacturer warranty.

## Credits

- [bkerler/mtkclient](https://github.com/bkerler/mtkclient) — the foundation that makes BROM access possible
- The Kamakiri exploit researchers
- Everyone who reported the seccfg bug on GitHub — your reports helped map the scope

## License

[AGPL-3.0](LICENSE) — If you use this code, you must publish your source code too. No closed-source paid tools.

---

Researched & tested by: **Jz8root**
