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

| Device (codename, model) | SoC | Storage | LK build | scan_lk verdict | Path | Result | Date | Tester |
|-|-|-|-|-|-|-|-|-|
| POCO M4 Pro 4G (fleur) | MT6781 Helio G96 | Samsung | HyperOS OS1.0.11.0.TKEEUXM (Oct 2024) | `COMPATIBLE_FULL` | A (RPMB erase sector 57344 + seccfg) | UNLOCKED | 2026-03-23 | Jz8root |
| POCO M4 Pro 4G (fleur, 2201117PG) | MT6781 Helio G96 | SK Hynix `H9QT1G6DN6X132` | HyperOS 1.0.2.0.TKEMIXM, exact slot hashes/builds pending [#19](https://github.com/Jz8Root/xiaomi-hyperos-bootloader-unlock/issues/19) | active `lk_b`: `COMPATIBLE_FULL` (100/100); `lk_a`: `COMPATIBLE_SECCFG_ONLY` | A (RPMB erase sector 57344 + seccfg, active slot B) | UNLOCKED, persistent | 2026-10-19 | staxifrage |
| Redmi Note 11S 4G (fleur, 2201117SY) | MT6781 Helio G96 | SK Hynix H9HQ54AECMMDAR | `fleur-d01540d34-20220430143603` md5 `701bbd3ee76e780b030d8568368a7a4e` (HyperOS V816.0.1.0.TKEEUXM, EEA) | `COMPATIBLE_SECCFG_ONLY` (52/100) | B (seccfg only) | UNLOCKED | 2026-05-19 | miromraz |
| Redmi Note 11S Global (miel, 2201117SG) | MT6781 Helio G96 | Samsung KM8L9001JM-B62 | `fleur-90fe266d7-20240412152854-20241206204609` (HyperOS OS1.0.9.0.TKEMIXM) | `COMPATIBLE_FULL` | A (RPMB erase sector 57344 + seccfg) | UNLOCKED | 2026-05 | itsme |
| Redmi Note 11S (miel, MT6781) | MT6781 Helio G96 | Samsung | HyperOS OS1.0.9.0.TKEEUXM | `COMPATIBLE_FULL` | A (RPMB erase sector 57344 + seccfg) | UNLOCKED | 2026-06-15 | kwhj4ff67r-crypto |
| Redmi Note 13 5G (gold) | MT6833 Dimensity 6080 | Samsung | HyperOS 3.0.9.0.VNQCNXM (Android 15) `gold-c2e4398a1-20260513092248-20260514074541` | `COMPATIBLE_FULL` (100/100) | A (RPMB erase **sector 65504** + seccfg) | UNLOCKED | 2026-06-15 | KTS618 |
| Redmi 12 (fire) | MT6769Z / Helio G88 | Samsung; exact ID not preserved, [Redmi 12 official specification](https://www.mi.com/global/product/redmi-12/specs/) is eMMC 5.1 | HyperOS 2.0.207 (Android 14) | `COMPATIBLE_FULL` (100/100, **slot B** — lk_a was SECCFG_ONLY) | A (RPMB erase sector 57344 + seccfg, active slot B) | UNLOCKED | 2026-06-16 | piotrurban |
| Redmi Note 12S (sea) | MT6781 Helio G96 | (not reported) | HyperOS 2.0.210.0 VHZMIXM | `COMPATIBLE_FULL` | A (RPMB erase sector 57344 + seccfg) | UNLOCKED | 2026-07-30 | katavnnn |
| POCO M4 5G (thunder, 22041219PG) | MT6833 Dimensity 700 | SanDisk UFS `SDINDDK4-64G`, MID `0x45` | `light-072f5dbd2-20231011161345-20250722115219` (HyperOS OS1.0.8.0.ULSEUXM, EEA) | `COMPATIBLE_FULL` (100/100) | A (RPMB erase **sector 57344** + seccfg, active slot A) | UNLOCKED, persistent | 2026-10-16 | [ogmkp](https://github.com/ogmkp), [#18](https://github.com/Jz8Root/xiaomi-hyperos-bootloader-unlock/issues/18) |

> **Note on miel:** `fastboot getvar version-bootloader` returns `fleur-90fe266d7-...` — Xiaomi ships the
> fleur LK binary on miel unchanged. The same recipe works without modification. RPMB dump shows magic at
> 4 locations (sector 16352, 57344, 81888, 122880); erasing sector 57344 only is sufficient — the other
> hits 16 MiB apart are aliases caused by the 16-bit RPMB frame address wrapping at 65536 sectors.
>
> **⚠️ RPMB sector is NOT universal — always locate the magic before erasing:**
> The sector where `Jz8PNRUF` lives is driver-family-dependent. Known measurements:
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

> **`thunder` acquisition detail:** the saved 2 MiB `lk_b` partition was entirely zero-filled
> (SHA-256 `5647f05ec18958947d32874eeb788fa396a05d0bab7c1b71f112ceb7e9b31eee`).
> The active `lk_a` matched the complete official `lk.img` byte-for-byte; the remaining partition
> tail was zero padding. This describes the captured device state, not every future OTA layout.

## Tier 2 — CONFIRMED COMPATIBLE VIA LK ANALYSIS (unlock pending)

| Device | SoC | Status |
|-|-|-|
| *(no entry currently meets the Tier 2 evidence bar)* | — | — |

## Tier 3 — INVESTIGATION REQUIRED

These devices have partial LK or hardware evidence but not enough live-state data
to select a safe path. They require both-slot LK scans and RPMB state collection;
the RPMB erase fix is a hypothesis, not a hardware-confirmed result.

| Device | SoC | Evidence / issue |
|--------|-----|-----------------|
| POCO M3 Pro / Redmi Note 10 5G (camellia) | MT6833 | Legacy LK sample exists; no current hardware report in this repository |
| Xiaomi 11T (agate) | MT6893 Dimensity 1200 | [#14](https://github.com/Jz8Root/xiaomi-hyperos-bootloader-unlock/issues/14) — Kamakiri confirmed; MIUI 12.5 token-gated case and HyperOS 1.0.15 LK investigation open |

`agate` is not a normal RPMB-fix prediction yet. On MIUI 12.5, a cold-read-verified
seccfg state 3 remained locked and the full RPMB dump contained no magic. A later
HyperOS 1.0.15 LK supplied by qqqZXzz123 scans `COMPATIBLE_FULL` and contains the
explicit string `1st time run MI Lock, write magic`, but no live RPMB state or
hardware unlock result has been supplied. Read-only device-state collection is
required before selecting a path.

## Tier 3b -- EARLY BOOT CHAIN RESTORES MAGIC (hard block, no bypass yet)

Kamakiri works, BROM is reachable, the RPMB reads and writes fine, and `scan_lk.py` returns
`COMPATIBLE_FULL`. The erase reaches flash and persists in a cold BROM re-read, but any boot
path restores the 8 magic bytes before fastboot can report the unlocked state. Fastboot
verification therefore always reports locked, even after a full erase + seccfg unlock sequence.
The responsible stage has not yet been isolated: current evidence bounds it to the normal boot
chain after cold BROM re-entry and before the lock result is exposed. **Two independent clusters,
same observed mechanism.**

### Cluster 1: MT6877

| Device | SoC | Storage | Reporter | Full sequence tested | Where |
|-|-|-|-|-|-|
| Redmi Note 12 Pro+ 5G (rubypro) | MT6877 | SK Hynix `H9QT1G6DN6X132` | LucaCraft89 | yes, locked after | [#13][i13], bkerler/mtkclient#305 |
| Redmi Note 11 Pro (pissarro) | MT6877 | Samsung `KM8F9001JM-B81` | burg1ar | yes, locked after | [#11][i11] |
| Redmi Note 11 Pro+ (pissarropro) | MT6877 / D920 | (not reported) | dexus19 | not reported | bkerler/mtkclient#305 |
| Redmi Note 12 Pro+ (IN variant) | MT6877 | (not reported) | RWBMAL | not reported | [#8][i8] |

### Cluster 2: `earth` (MT6769 family, eMMC)

| Device | SoC | Storage | Reporter | Full sequence tested | Where |
|-|-|-|-|-|-|
| Redmi 12C (earth) | MT6769Z | eMMC `Y2P064` | ssg-enjoyer | yes, locked after | [#8][i8] |
| Redmi 12C (earth) | MT6768/MT6769 | eMMC `Y2P064` | vivaad | yes, locked after + preloader boot1 dump has no literal `Jz8PNRUF` | [#8][i8] |

**Related unresolved case:** a Redmi 12 reported as `fire` with eMMC `Y0S256` ([#10](https://github.com/Jz8Root/xiaomi-hyperos-bootloader-unlock/issues/10)) remains locked after persistent V4 seccfg writes. Both LK slots lack the literal magic but contain `mi_get_lock_state` and the RPMB primitives. No RPMB dump or `fastboot getvar product` output was supplied, so it is not yet classified as Tier 3b. The confirmed Tier 1 `fire` row records Samsung storage but its original evidence does not identify UFS versus eMMC; Xiaomi's [official Redmi 12 specification](https://www.mi.com/global/product/redmi-12/specs/) says eMMC 5.1. Storage type alone therefore does not explain the split.

### What has been measured

**On rubypro (LucaCraft89):**

- Controller accepts the write, `resp=0` with the [mtkclient#307](https://github.com/bkerler/mtkclient/pull/307) reporting fix applied (merged August 2026)
- Writing `0xAA` across the whole 256-byte sector, then reading cold, shows 248 bytes persisted and only the 8 magic bytes reverted to `Jz8PNRUF`
- A same-session re-read shows the magic gone, which is a false positive (see README on cold verification)
- Full `erase -> reset -> seccfg unlock -> reset -> fastboot` sequence runs cleanly and ends with `unlocked: no`

**On pissarro (burg1ar):**

- Same symptom as rubypro, Samsung UFS instead of SK Hynix: `erase + seccfg unlock` in a single DA session, seccfg reports `Device is already unlocked`, fastboot returns `unlocked: no`. The UFS vendor is not the variable.

**On earth (vivaad):**

- Erase at sector 57344, immediate readback shows the sector zeroed
- seccfg forced to `lock_state=3`, `dm_verity_state=1`
- After `mtk.py reset` and a cold volume-key BROM re-entry, the sector is still all zero
- After allowing the phone to reach the Mi logo, exactly bytes 0-7 return to `Jz8PNRUF`; bytes 8-255 remain zero
- Fastboot returns `unlocked: no`
- The preloader boot1 dump (`mtk.py r preloader --parttype=boot1`) does **not** contain the literal string `Jz8PNRUF`

### What is still open

The restoration mechanism is not fully characterised yet. The cold-cycle experiment proves that
the write happens during the normal boot chain, but reaching the Mi logo does not distinguish the
preloader, another loader, ATF/TEE or LK. On MT6877 and `earth` it fires on every tested boot;
on Tier 1 devices it does not restore the magic after the successful sequence. The realistic next
step is tracing the LK magic-write callers first, then following cross-references into earlier boot
stages where the evidence points.

### What would help

If you own one of these devices, three things move the needle:

1. Preserve minimal before/after proof: the 256-byte magic sector after cold BROM re-entry and after a normal boot, or at least SHA-256 hashes plus byte-level diffs.
2. Share both LK slots, exact build strings, `scan_lk.py --json` output and preloader/boot1/boot2 hashes. Raw private dumps are not required if the relevant binaries and offsets can be isolated.
3. Trace the magic writer and its callers in Ghidra. Cross-device comparison between blocked `earth`/MT6877 builds and working `fire`/MT6781 builds is now more useful than repeating untargeted erase cycles.

## Tier 4 — NO CONFIRMED ACCESS PATH IN THIS PROJECT

These raw SoC families currently have no project-verified Kamakiri/BROM path for
this method. This is a research status, not proof that every device using the SoC
is permanently inaccessible.

| SoC family | Project status |
|-----|-----------------|
| MT6789 / MT8781V | No confirmed path |
| MT6855 | No confirmed path |
| MT6895 | No confirmed path |
| MT6983 | No confirmed path |
| MT6989 | No confirmed path |

> **⚠️ Do not judge Kamakiri support by comparing SoC numbers.** MediaTek part numbers are not
> chronological, so "MT6789 or newer" cannot be read as "greater than 6789". MT6877 and MT6893
> were previously listed here on that faulty inference; hardware logs now confirm Kamakiri on
> both. Redmi Note 12S (`sea`) was also listed here while actually being an MT6781, now Tier 1.
> Classify the exact SoC and observed BROM exchange, not a marketing-name guess or a greater-than
> comparison.

**All Snapdragon devices** are out of scope (completely different bootloader architecture).

## Firmware → Likely Verdict (rule of thumb)

The verdict from `scan_lk.py` is the binary decision gate, not proof of live RPMB initialization.
Use this table only as a prior expectation:

| Firmware era | Likely scan_lk verdict | Notes |
|-|-|-|
| HyperOS 1 (2024, OS1.0.x) — fresh-shipped device | `COMPATIBLE_FULL` (Path A) | LK rebuilt for RPMB magic — magic present, erase needed |
| HyperOS 1 (2024, OS1.0.x) — updated *from* MIUI without LK rewrite | `COMPATIBLE_SECCFG_ONLY` (Path B) | Older LK never updated despite Android version bump (observed on fleur 2201117SY) |
| HyperOS 2 (2025) | `COMPATIBLE_FULL` (Path A) | Confirmed on fire/MT6769Z (piotrurban). lk_a/lk_b can diverge after OTA — scan both slots |
| HyperOS 3 (2026, OS3.0.x, Android 15) | `COMPATIBLE_FULL` (Path A) | Confirmed on gold/MT6833 (KTS618). RPMB sector may differ from MT6781 — always grep the dump |
| MIUI 14 (2023) | Varies | Some shipped with the new lock; many didn't |
| MIUI 13 (2022) and earlier | Varies | Many builds are Path B, but `agate` MIUI 12.5 is a counterexample: persistent seccfg state 3 remained locked with no live RPMB magic |

---

**Want to contribute?** Test the method on your device and open an issue with:
- Device model + codename + submodel suffix (e.g. `2201117SY`)
- SoC
- Firmware version
- Storage identifier (from `DAXFlash - UFS ID:` or `DAXFlash - EMMC ID:`)
- LK build string and SHA-256 (look in the LK binary with `strings lk_a.bin | grep -E '<codename>-'`)
- `scan_lk.py --json` output
- `fastboot oem lks` output after the procedure

[i8]: https://github.com/Jz8Root/xiaomi-hyperos-bootloader-unlock/issues/8
[i11]: https://github.com/Jz8Root/xiaomi-hyperos-bootloader-unlock/issues/11
[i13]: https://github.com/Jz8Root/xiaomi-hyperos-bootloader-unlock/issues/13
