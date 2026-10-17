# Compatibility Database

> **Indexed by LK build, not codename.** The same codename (e.g. fleur) ships multiple LK
> generations across different firmware versions and submodels — and they don't all
> implement the RPMB magic check. Always run `scan_lk.py` on the LK extracted from
> your specific device before assuming a row below applies to you.
>
> **Quick compatibility filter:** run `fastboot getvar version-bootloader`. If the output
> starts with `fleur-`, your device ships the fleur LK binary and this procedure applies
> unchanged. Confirmed on miel (Redmi Note 11S) — same binary, same recipe, same result.

## Tier 1 — PROVEN ON HARDWARE

| Device (codename, model) | SoC | UFS vendor | LK build | scan_lk verdict | Path | Result | Date | Tester |
|-|-|-|-|-|-|-|-|-|
| POCO M4 Pro 4G (fleur) | MT6781 Helio G96 | Samsung | HyperOS OS1.0.11.0.TKEEUXM (Oct 2024) | `COMPATIBLE_FULL` | A (RPMB erase sector 57344 + seccfg) | UNLOCKED | 2026-03-23 | Jz8root |
| Redmi Note 11S 4G (fleur, 2201117SY) | MT6781 Helio G96 | SK Hynix H9HQ54AECMMDAR | `fleur-d01540d34-20220430143603` md5 `701bbd3ee76e780b030d8568368a7a4e` (HyperOS V816.0.1.0.TKEEUXM, EEA) | `COMPATIBLE_SECCFG_ONLY` (52/100) | B (seccfg only) | UNLOCKED | 2026-05-19 | miromraz |
| Redmi Note 11S Global (miel, 2201117SG) | MT6781 Helio G96 | Samsung KM8L9001JM-B62 | `fleur-90fe266d7-20240412152854-20241206204609` (HyperOS OS1.0.9.0.TKEMIXM) | `COMPATIBLE_FULL` | A (RPMB erase sector 57344 + seccfg) | UNLOCKED | 2026-05 | itsme |
| Redmi Note 11S (miel, MT6781) | MT6781 Helio G96 | Samsung | HyperOS OS1.0.9.0.TKEEUXM | `COMPATIBLE_FULL` | A (RPMB erase sector 57344 + seccfg) | UNLOCKED | 2026-06-15 | kwhj4ff67r-crypto |
| Redmi Note 13 5G (gold) | MT6833 Dimensity 6080 | Samsung | HyperOS 3.0.9.0.VNQCNXM (Android 15) `gold-c2e4398a1-20260513092248-20260514074541` | `COMPATIBLE_FULL` (100/100) | A (RPMB erase **sector 65504** + seccfg) | UNLOCKED | 2026-06-15 | KTS618 |
| Redmi 12 (fire) | MT6769Z Helio G85 | Samsung | HyperOS 2.0.207 (Android 14) | `COMPATIBLE_FULL` (100/100, **slot B** — lk_a was SECCFG_ONLY) | A (RPMB erase sector 57344 + seccfg, active slot B) | UNLOCKED | 2026-06-16 | piotrurban |
| Redmi Note 12S (sea) | MT6781 Helio G96 | (not reported) | HyperOS 2.0.210.0 VHZMIXM | `COMPATIBLE_FULL` | A (RPMB erase sector 57344 + seccfg) | UNLOCKED | 2026-07-30 | katavnnn |
| POCO M4 5G (thunder, 22041219PG) | MT6833 Dimensity 700 | SanDisk SDINDDK4-64G | `light-072f5dbd2-20231011161345-20250722115219` (HyperOS OS1.0.8.0.ULSEUXM, EEA) | `COMPATIBLE_FULL` (100/100) | A (RPMB erase **sector 57344** + seccfg) | UNLOCKED | 2026-10-16 | ogmkp |

> **Note on miel:** `fastboot getvar version-bootloader` returns `fleur-90fe266d7-...` — Xiaomi ships the
> fleur LK binary on miel unchanged. The same recipe works without modification. RPMB dump shows magic at
> 4 locations (sector 16352, 57344, 81888, 122880); erasing sector 57344 only is sufficient — the other
> copies appear to be UFS RPMB address space mirroring (lower 16 MB mirrored to upper 16 MB).
>
> **⚠️ RPMB sector is NOT universal — always locate the magic before erasing:**
> The sector where `Jz8PNRUF` lives in the RPMB dump is SoC-dependent. Known values:
> - MT6781 (Helio G96): sector **57344** (dump offset `0xE00000`)
> - MT6833 (Dimensity 6080, gold LK): sector **65504** (dump offset `0xFFE000`) -- discovered by KTS618
> - MT6833 (Dimensity 700, light LK): sector **57344** (dump offset `0xE00000`) -- discovered by ogmkp
>
> **MT6833 has two known sectors depending on the LK driver family.** The gold and light LK
> builds use different RPMB offset logic internally. Do not assume 65504 just because your
> device is MT6833. Always grep the dump first.
>
> To find the correct sector on your device: dump RPMB with `python3 mtk.py da rpmb r rpmb_dump.bin`,
> then run `grep -boa "Jz8PNRUF" rpmb_dump.bin` -- the byte offset divided by 256 gives your sector number.

## Tier 2 — CONFIRMED COMPATIBLE VIA LK ANALYSIS (unlock pending)

| Device | SoC | Status |
|-|-|-|
| *(no entries — all analyzed devices have now been tested on hardware)* | — | — |

## Tier 3 — PROBABLE (GitHub issues confirm same symptom)

These devices have documented mtkclient issues with the exact same problem: "seccfg unlock succeeds but bootloader stays locked." The RPMB erase fix is the logical answer.

| Device | SoC | mtkclient Issue |
|--------|-----|-----------------|
| POCO M3 Pro / Redmi Note 10 5G (camellia) | MT6833 | #764 |
| Redmi 10 5G | MT6833 | #764 |
| Redmi Note 8 Pro / POCO X2 (begonia) | MT6785 | #1219 |
| Redmi Note 9 Pro 5G / Mi 10T Lite | MT6873 | — |
| Redmi Note 9 5G / Note 9T | MT6853 | — |
| Redmi 9 / Note 9 (lancelot) | MT6769 | — |
| Redmi 12C (earth) | MT6765 | — |
| Redmi 10C / 10A / 9A / 9C | MT6762 | #81 #738 #1405 |

Issues #81 and #738 have been open since **2021**.

## Tier 3b — BROM ACCESSIBLE, ERASE DOES NOT PERSIST (under investigation)

Kamakiri works, BROM is reachable, the RPMB reads and writes fine, and `scan_lk.py` returns
`COMPATIBLE_FULL`. What fails is that the erased magic is back after a power cycle. Four
independent reports, one SoC.

| Device | SoC | Storage | Reporter | Where |
|-|-|-|-|-|
| Redmi Note 12 Pro+ 5G (rubypro) | MT6877 | SK Hynix `H9QT1G6DN6X132` | LucaCraft89 | [#13][i13], bkerler/mtkclient#305 |
| Redmi Note 11 Pro (pissarrro) | MT6877 | (not reported) | burg1ar | [#11][i11] |
| Redmi Note 11 Pro+ (pissarropro) | MT6877 / D920 | (not reported) | dexus19 | bkerler/mtkclient#305 |
| Redmi Note 12 Pro+ (IN variant) | MT6877 | (not reported) | RWBMAL | [#8][i8] |

What has been measured so far, on rubypro:

- the controller accepts the write, `resp=0` with the [mtkclient#307](https://github.com/bkerler/mtkclient/pull/307) reporting fix applied
- writing `0xAA` across the whole 256-byte sector, then reading cold, shows 248 bytes persisted
  and only the 8 magic bytes reverted to `Jz8PNRUF`
- a same-session re-read shows the magic gone, which is a false positive, see the README

Two candidate explanations are still open: a boot stage restoring the field, or the field being
regenerated below the write path. If you own one of these devices, a dump before and after a
genuine cold cycle is the most useful thing you can contribute.

## Tier 4 — NOT COMPATIBLE (BROM V6 — Kamakiri patched in hardware)

| SoC | Example Devices |
|-----|-----------------|
| MT6789 / Helio G99 | POCO M5 |
| MT6855 / Dimensity 8100 | POCO F5 |
| MT6893 / Dimensity 1200 | Redmi K40 Gaming |
| MT6895 / Dimensity 8200 | Redmi Note 12 Turbo Pro |
| MT6983 / Dimensity 9000+ | Xiaomi 13, 13T |
| MT6989 / Dimensity 9300 | Xiaomi 14T Pro |

> **⚠️ Do not judge Kamakiri support by comparing SoC numbers.** MediaTek part numbers are not
> chronological, so "MT6789 or newer" cannot be read as "greater than 6789". The MT6877 is a 2021
> part, older than the 2022 MT6789, and Kamakiri runs on it. Release order for the parts that
> matter here:
>
> | Year | SoC | Kamakiri |
> |-|-|-|
> | 2020 | MT6833 | works |
> | 2021 | MT6781 | works |
> | 2021 | MT6877 | works |
> | 2022 | MT6789 | patched |
> | 2022 | MT6855 | patched |
>
> MT6877 was previously listed in Tier 4 on that faulty reading. It is not BROM V6, and the
> Redmi Note 12S (sea) was listed there too while actually being an MT6781, now Tier 1.

**All Snapdragon devices** are out of scope (completely different bootloader architecture).

## Firmware → Likely Verdict (rule of thumb)

The verdict from `scan_lk.py` on your specific LK is authoritative. Use this table only as a
prior expectation:

| Firmware era | Likely scan_lk verdict | Notes |
|-|-|-|
| HyperOS 1 (2024, OS1.0.x) — fresh-shipped device | `COMPATIBLE_FULL` (Path A) | LK rebuilt for RPMB magic — magic present, erase needed |
| HyperOS 1 (2024, OS1.0.x) — updated *from* MIUI without LK rewrite | `COMPATIBLE_SECCFG_ONLY` (Path B) | Older LK never updated despite Android version bump (observed on fleur 2201117SY) |
| HyperOS 2 (2025) | `COMPATIBLE_FULL` (Path A) | Confirmed on fire/MT6769Z (piotrurban). lk_a/lk_b can diverge after OTA — scan both slots |
| HyperOS 3 (2026, OS3.0.x, Android 15) | `COMPATIBLE_FULL` (Path A) | Confirmed on gold/MT6833 (KTS618). RPMB sector may differ from MT6781 — always grep the dump |
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

[i8]: https://github.com/Jz8Root/xiaomi-hyperos-bootloader-unlock/issues/8
[i11]: https://github.com/Jz8Root/xiaomi-hyperos-bootloader-unlock/issues/11
[i13]: https://github.com/Jz8Root/xiaomi-hyperos-bootloader-unlock/issues/13
