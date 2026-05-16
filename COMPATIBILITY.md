# Compatibility Database

## Tier 1 — PROVEN ON HARDWARE

| Device | SoC | Exploit | Result | Date |
|--------|-----|---------|--------|------|
| POCO M4 Pro 4G (fleur) | MT6781 Helio G96 | Kamakiri2 | UNLOCKED | 2026-03-23 |

## Tier 2 — CONFIRMED COMPATIBLE VIA LK ANALYSIS (unlock pending)

| Device | SoC | Status |
|--------|-----|--------|
| Redmi Note 11S (miel) | MT6781 | LK binary analyzed — magic, RSA key, offsets all match. Hardware test scheduled. |

## Tier 3 — PROBABLE (GitHub issues confirm same symptom)

These devices have documented mtkclient issues with the exact same problem: "seccfg unlock succeeds but bootloader stays locked." The RPMB erase fix is the logical answer.

| Device | SoC | mtkclient Issue |
|--------|-----|-----------------|
| POCO M3 Pro / Redmi Note 10 5G (camellia) | MT6833 | #764 |
| POCO M4 5G / Redmi 10 5G | MT6833 | #764 |
| Redmi Note 8 Pro / POCO X2 (begonia) | MT6785 | #1219 |
| Redmi Note 9 Pro 5G / Mi 10T Lite | MT6873 | — |
| Redmi Note 9 5G / Note 9T | MT6853 | — |
| Redmi 9 / Note 9 (lancelot) | MT6769 | — |
| Redmi 12C (earth) | MT6765 | — |
| Redmi 10C / 10A / 9A / 9C | MT6762 | #81 #738 #1405 |

Issues #81 and #738 have been open since **2021**.

## Tier 4 — NOT COMPATIBLE (BROM V6 — Kamakiri patched in hardware)

| SoC | Example Devices |
|-----|-----------------|
| MT6877 / Dimensity 920 | Redmi Note 11 Pro (pissarro) |
| MT6893 / Dimensity 1080 | Redmi Note 12 Pro |
| MT6789 / Helio G99 | POCO M5, Redmi Note 12S |
| MT6855 / Dimensity 8100 | POCO F5 |
| MT6895 / Dimensity 8200 | Redmi Note 12 Turbo Pro |
| MT6983 / Dimensity 9000+ | Xiaomi 13, 13T |
| MT6989 / Dimensity 9300 | Xiaomi 14T Pro |

**All Snapdragon devices** are out of scope (completely different bootloader architecture).

## Firmware Method Reference

| Firmware | RPMB lock present | Method |
|----------|-------------------|--------|
| HyperOS 1 (2024, OS1.0.x) | YES — tested | RPMB erase + seccfg unlock |
| HyperOS 2/3 (2025-2026) | UNKNOWN | Not tested — use with caution |
| MIUI 14 (2023) | Varies | Scan your LK binary with scan_lk.py |
| MIUI 13 (2022) | NO | seccfg only |
| MIUI 11/12 (2021) | NO | seccfg only |

## Tested By

| Tester | Device | Result | Date |
|--------|--------|--------|------|
| Jz8root | POCO M4 Pro 4G (fleur, MT6781, HyperOS OS1.0.11.0.TKEEUXM) | UNLOCKED | 2026-03-23 |

---

**Want to contribute?** Test the method on your device and open an issue with:
- Device model + codename
- SoC
- Firmware version
- `fastboot oem lks` output after the procedure
- scan_lk.py output (`--json`)
