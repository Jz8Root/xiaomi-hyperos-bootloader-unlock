# Compatibility Database

> **Indexed by LK build, not codename.** The same codename (e.g. fleur) ships multiple LK
> generations across different firmware versions and submodels — and they don't all
> implement the RPMB magic check. Always run `scan_lk.py` on the LK extracted from
> your specific device before assuming a row below applies to you.

## Tier 1 — PROVEN ON HARDWARE

| Device (codename, model) | SoC | UFS vendor | LK build | scan_lk verdict | Path | Result | Date | Tester |
|-|-|-|-|-|-|-|-|-|
| POCO M4 Pro 4G (fleur) | MT6781 Helio G96 | Samsung | HyperOS OS1.0.11.0.TKEEUXM (Oct 2024) | `COMPATIBLE_FULL` | A (RPMB erase + seccfg) | UNLOCKED | 2026-03-23 | Jz8root |
| Redmi Note 11 4G (fleur, 2201117SY) | MT6781 Helio G96 | SK Hynix H9HQ54AECMMDAR | `fleur-d01540d34-20220430143603` md5 `701bbd3ee76e780b030d8568368a7a4e` (HyperOS V816.0.1.0.TKEEUXM, EEA) | `COMPATIBLE_SECCFG_ONLY` (52/100) | B (seccfg only) | UNLOCKED | 2026-05-19 | miromraz |

## Tier 2 — CONFIRMED COMPATIBLE VIA LK ANALYSIS (unlock pending)

| Device | SoC | Status |
|-|-|-|
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

## Firmware → Likely Verdict (rule of thumb)

The verdict from `scan_lk.py` on your specific LK is authoritative. Use this table only as a
prior expectation:

| Firmware era | Likely scan_lk verdict | Notes |
|-|-|-|
| HyperOS 1 (2024, OS1.0.x) — fresh-shipped device | `COMPATIBLE_FULL` (Path A) | LK rebuilt for RPMB magic — magic present, erase needed |
| HyperOS 1 (2024, OS1.0.x) — updated *from* MIUI without LK rewrite | `COMPATIBLE_SECCFG_ONLY` (Path B) | Older LK never updated despite Android version bump (observed on fleur 2201117SY) |
| HyperOS 2/3 (2025+) | UNKNOWN | Not yet observed — run `scan_lk.py` and report |
| MIUI 14 (2023) | Varies | Some shipped with the new lock; many didn't |
| MIUI 13 (2022) and earlier | `COMPATIBLE_SECCFG_ONLY` (Path B) | Pre-dates the RPMB lock layer entirely |

---

**Want to contribute?** Test the method on your device and open an issue with:
- Device model + codename + submodel suffix (e.g. `2201117SY`)
- SoC
- Firmware version
- UFS vendor (from mtkclient log: `DAXFlash - UFS ID: ...`)
- LK build string and md5 (look in the LK binary with `strings lk_a.bin | grep -E '<codename>-'`)
- `scan_lk.py --json` output
- `fastboot oem lks` output after the procedure
