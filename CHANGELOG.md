# Changelog

## 2026-10-28 -- Evidence Audit + Scanner Safety Gates

- `COMPATIBLE_FULL` now requires detected seccfg support and describes LK capability rather than claiming live RPMB initialization from a binary scan
- A magic-absent LK that still exposes exact `mi_get_lock_state` now returns `MAYBE` instead of the destructive false-Path-B result observed in issue #10
- Added scanner regressions for full Path A, clean Path B, contradictory RPMB signals, missing seccfg and preloader-like input
- First-boot wipe guidance is now conditional: issue #18 booted without an explicit userdata/metadata erase, so documentation says to assume data loss without claiming every build requires the same wipe
- Removed dead legacy issue references and unsupported device/SoC pairings from speculative compatibility tiers
- Corrected sector language from SoC-specific to LK/storage-driver-family-specific and replaced the old miel "mirroring" explanation with the measured 16-bit address alias

## 2026-10-22 -- MT6893 Reclassification + HyperOS Agate LK

- qqqZXzz123 supplied an 8 MiB Xiaomi 11T (`agate`, MT6893) LK from HyperOS 1.0.15.0.UKWRUXM in #14; SHA-256 `f5c058d02e214009aa32456d6eb0f844d3492f9b713bee1702ab4919d856328c`
- The LK scans `COMPATIBLE_FULL` (100/100), contains `Jz8PNRUF` at `0x0011D808`, and exposes the explicit initialization string `1st time run MI Lock, write magic`
- This is not yet a hardware unlock confirmation: active slot, second LK slot, live RPMB state, storage identifier and fastboot lock state are still pending
- MT6893 removed from Tier 4. av2xn's original #14 log proves Kamakiri executes successfully on this 2021 SoC; its unlock architecture remains unresolved

## 2026-10-19 -- Fleur Slot Divergence Confirmation + Earth Cold-BROM Isolation

- POCO M4 Pro 4G (`fleur`, 2201117PG, MT6781, SK Hynix `H9QT1G6DN6X132`) independently confirmed unlocked and persistent by staxifrage in #19 on HyperOS 1.0.2.0.TKEMIXM
- New slot-divergence confirmation: `lk_a` scanned `COMPATIBLE_SECCFG_ONLY`, active `lk_b` scanned `COMPATIBLE_FULL` (100/100). This reproduces the earlier `fire` A/B split on a second device family and reinforces the rule to scan both slots
- The successful erase on the same SK Hynix part used by blocked `rubypro` hardware rules out the UFS vendor and part number as the Tier 3b cause
- vivaad completed the decisive `earth` cold-cycle test in #8: sector 57344 stayed zero after `mtk.py reset` plus cold BROM re-entry, then exactly the 8 magic bytes returned after the Mi logo appeared
- Attribution corrected from `preloader restores the magic` to `early boot chain restores the magic`. The experiment bounds the writer to a normal boot stage but does not distinguish preloader, another loader, ATF/TEE or LK

## 2026-10-17 -- Eighth Hardware Unlock + MT6833 Sector Correction

- POCO M4 5G (thunder, 22041219PG, MT6833/Dimensity 700, SanDisk UFS) confirmed unlocked by ogmkp -- eighth Tier 1 device, second MT6833 confirmation
- Key finding: **MT6833 sector depends on the LK driver family, not the SoC alone.** The gold LK uses sector 65504, but the light LK uses sector 57344. ogmkp decompiled the LK driver and traced the divergence to an internal `uxth` truncation at offset `0x6AD96`. Two MT6833 devices with different LK families produce different sectors
- scan_lk.py: `known_sectors` table now splits MT6833 into `MT6833/gold` (65504) and `MT6833/light` (57344). Verdict message generated dynamically from the table instead of hardcoded
- COMPATIBILITY.md: thunder/light added to Tier 1, POCO M4 5G removed from Tier 3. MT6833 sector warning added
- ogmkp also identified two mtkclient bugs: UFS literal-pool alignment in `XFlashExt.patch()` (the DA pointer is read 2 bytes off when an alignment NOP is present), now proposed in [mtkclient#426](https://github.com/bkerler/mtkclient/pull/426), and MEID not restored in `DAloader.reinit()`, proposed separately in [mtkclient#427](https://github.com/bkerler/mtkclient/pull/427)

## 2026-10-05 -- Redmi Note 13 5G Independent Confirmation

- Redmi Note 13 5G (gold, MT6833) independently confirmed unlocked by Gkhupo (#17) -- second successful unlock on this SoC/LK combination, replicating KTS618's June result

## 2026-07-31 -- MT6877 Reclassification + Boot-Time Restoration Discovery + scan_lk Fixes

- **Discovery: a normal boot path rewrites the RPMB magic.** The Power button is forbidden between erase and unlock because reaching the Mi logo is enough to restore the magic. LucaCraft89's three-dump sequence on rubypro (SK Hynix UFS, MT6877) proved the magic absent after cold BROM re-entry and present again after a normal start-up. The responsible stage was initially attributed to the preloader; vivaad's later cold-cycle test bounds it only to the early boot chain
- MT6877 reclassified from Tier 4 (BROM V6) to Tier 3b. MT6877 is a 2021 part, not a 2022 part -- Kamakiri runs on it. Other Tier 4 device/SoC mappings were also corrected
- USB 3.0 silent write corruption documented: RPMB writes acknowledged by mtkclient but never committed to flash on certain USB 3.0 host controllers. Warnings restructured, 3 FAQ entries added
- RPMB addressing corrected: sector depends on the SoC (now further refined to LK family), not the storage vendor. The documented 57344 sector was the modular wrap of the LK-internal offset, not a mirroring artifact
- Power-down procedure changed from "unplug, force-off" (which starts the normal boot chain) to `mtk.py reset` DA shutdown (untested on hardware at the time, later validated by vivaad)
- scan_lk.py: RPMB size-constant check removed from scoring (matched preloaders). Points redistributed: magic 40->47, RSA 15->18, seccfg 15->18, functions 15->17. Path B verdict now gated on evidence (RSA key or functions), not raw score, to prevent the ceiling regression from misclassifying working devices
- Issue template: stopped suggesting 57344 as the default RPMB sector
- PR bkerler/mtkclient#307 opened and merged (02 August): fix silent discard of RPMB error codes in `custom_rpmb_write()`

## 2026-06-16 -- v2.0.0: 6 Devices, 3 SoCs, Full HyperOS Lifecycle
- Redmi 12 (fire, MT6769Z/Helio G88, HyperOS 2.0.207) confirmed unlocked by piotrurban — first HyperOS 2.0 confirmation
- Key finding: lk_a and lk_b can carry different LK builds after OTA — slot A was COMPATIBLE_SECCFG_ONLY, slot B was COMPATIBLE (100/100). Always scan both slots.
- MT6769Z RPMB sector confirmed at 57344 (same as MT6781)

## 2026-06-15 — Fourth and Fifth Hardware Unlocks + New SoC
- Redmi Note 13 5G (gold, MT6833/Dimensity 6080, HyperOS 3.0.9.0/Android 15) confirmed unlocked by KTS618 — first HyperOS 3.0 confirmation
- Key finding: RPMB magic at sector 65504 on the MT6833 `gold` build (not 57344). This first showed the sector was not universal; later `light` evidence refined the variable to LK driver family. Always grep the dump before erasing.
- Redmi Note 11S (miel, MT6781, HyperOS 1.0.9.0) confirmed unlocked by kwhj4ff67r-crypto — independent replication of ITSME's result
- Step 0 added to procedure: mandatory sector discovery via `grep -boa "Jz8PNRUF" rpmb_dump.bin`
- FAQ updated for A/B slot divergence after OTA
- RPMB sector reference table expanded with MT6833 and MT6769Z entries
- HyperOS lifecycle fully covered: 1 (original PoC), 2 (piotrurban), 3 (KTS618)

## 2026-05-23 — Third Hardware Unlock + Cross-Device LK Discovery
- Redmi Note 11S Global (miel, 2201117SG, MT6781) confirmed unlocked on hardware by community tester (itsme)
- Key finding: `fastboot getvar version-bootloader` returns `fleur-90fe266d7-...` — Xiaomi ships the same fleur LK binary on miel unchanged
- New quick-filter: any MT6781 device reporting `version-bootloader: fleur-*` is compatible with this exact recipe
- RPMB dump analysis: magic present at 4 locations (sectors 16352, 57344, 81888, 122880); erasing sector 57344 alone is sufficient
- miel promoted from Tier 2 → Tier 1 in COMPATIBILITY.md
- mi_check_magic() boot flow diagram added to README

## 2026-05-16 — Phase 3: Full Method Released
- Full technical writeup published on XDA
- Root cause disclosed: dual-layer RPMB + seccfg lock verification
- 3-command unlock procedure documented
- Compatibility database with Tier 1-4 devices
- RPMB sector reference for multiple UFS types
- scan_lk.py compatibility scanner released
- Hidden fastboot OEM commands documented

## 2026-04-20 — Second Device LK Analysis
- Analyzed Redmi Note 11S (miel, MT6781) LK binary from community tester
- Magic, RSA key fingerprint, RPMB offsets all match reference
- Device confirmed compatible, hardware test scheduled

## 2026-04-04 — XDA PoC Post
- Initial Proof of Concept post published on XDA under Jz8root
- Method redacted, call for testers issued

## 2026-03-24 — Compatibility Research
- Scanned LK binaries across MT6781, MT6833, MT6785
- Confirmed universal Xiaomi MTK RSA-2048 key (fingerprint B7FBCDE320B827E3)
- Built compatibility database from mtkclient GitHub issues

## 2026-03-23 — Discovery
- Bootloader unlock achieved on POCO M4 Pro 4G (fleur, MT6781, HyperOS OS1.0.11.0)
- Root cause identified: RPMB magic override prevents seccfg unlock on HyperOS
- Full lock/unlock/relock cycle confirmed on hardware
- Method: RPMB erase (sector 57344) + seccfg unlock
