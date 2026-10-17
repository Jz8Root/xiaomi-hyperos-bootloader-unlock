# Changelog

## 2026-10-17 -- Eighth Hardware Unlock + MT6833 Sector Correction

- POCO M4 5G (thunder, 22041219PG, MT6833/Dimensity 700, SanDisk UFS) confirmed unlocked by ogmkp -- eighth Tier 1 device, second MT6833 confirmation
- Key finding: **MT6833 sector depends on the LK driver family, not the SoC alone.** The gold LK uses sector 65504, but the light LK uses sector 57344. ogmkp decompiled the LK driver and traced the divergence to an internal `uxth` truncation at offset `0x6AD96`. Two MT6833 devices with different LK families produce different sectors
- scan_lk.py: `known_sectors` table now splits MT6833 into `MT6833/gold` (65504) and `MT6833/light` (57344). Verdict message generated dynamically from the table instead of hardcoded
- COMPATIBILITY.md: thunder/light added to Tier 1, POCO M4 5G removed from Tier 3. MT6833 sector warning added
- ogmkp also identified two mtkclient bugs: UFS literal-pool alignment in `XFlashExt.patch()` (the DA pointer is read 2 bytes off when an alignment NOP is present), and MEID not restored in `DAloader.reinit()`. PRs pending upstream

## 2026-10-05 -- Redmi Note 13 5G Independent Confirmation

- Redmi Note 13 5G (gold, MT6833) independently confirmed unlocked by Gkhupo (#17) -- second successful unlock on this SoC/LK combination, replicating KTS618's June result

## 2026-07-31 -- MT6877 Reclassification + Preloader Discovery + scan_lk Fixes

- **Discovery: the preloader rewrites the RPMB magic on every boot.** The Power button is forbidden between erase and unlock because even reaching the Mi logo triggers the preloader, which restores the magic. Proven by LucaCraft89's three-dump sequence on rubypro (SK Hynix UFS, MT6877): magic absent after cold BROM re-entry, present again after any power-on
- MT6877 reclassified from Tier 4 (BROM V6) to Tier 3b. MT6877 is a 2021 part, not a 2022 part -- Kamakiri runs on it. Three other Tier 4 entries corrected (MT6893/Dimensity 1080 mislabel, Redmi Note 12S wrong SoC)
- USB 3.0 silent write corruption documented: RPMB writes acknowledged by mtkclient but never committed to flash on certain USB 3.0 host controllers. Warnings restructured, 3 FAQ entries added
- RPMB addressing corrected: sector depends on the SoC (now further refined to LK family), not the storage vendor. The documented 57344 sector was the modular wrap of the LK-internal offset, not a mirroring artifact
- Power-down procedure changed from "unplug, force-off" (which reboots and triggers the preloader) to `mtk.py reset` DA shutdown (untested on hardware, flagged as such)
- scan_lk.py: RPMB size-constant check removed from scoring (matched preloaders). Points redistributed: magic 40->47, RSA 15->18, seccfg 15->18, functions 15->17. Path B verdict now gated on evidence (RSA key or functions), not raw score, to prevent the ceiling regression from misclassifying working devices
- Issue template: stopped suggesting 57344 as the default RPMB sector
- PR bkerler/mtkclient#307 opened and merged (02 August): fix silent discard of RPMB error codes in `custom_rpmb_write()`

## 2026-06-16 -- v2.0.0: 6 Devices, 4 SoCs, Full HyperOS Lifecycle
- Redmi 12 (fire, MT6769Z, HyperOS 2.0.207) confirmed unlocked by piotrurban — first HyperOS 2.0 confirmation
- Key finding: lk_a and lk_b can carry different LK builds after OTA — slot A was COMPATIBLE_SECCFG_ONLY, slot B was COMPATIBLE (100/100). Always scan both slots.
- MT6769Z RPMB sector confirmed at 57344 (same as MT6781)

## 2026-06-15 — Fourth and Fifth Hardware Unlocks + New SoC
- Redmi Note 13 5G (gold, MT6833/Dimensity 6080, HyperOS 3.0.9.0/Android 15) confirmed unlocked by KTS618 — first HyperOS 3.0 confirmation
- Key finding: RPMB magic at sector 65504 on MT6833 (not 57344). Sector is SoC-specific — always grep the dump before erasing.
- Redmi Note 11S (miel, MT6781, HyperOS 1.0.9.0) confirmed unlocked by kwhj4ff67r-crypto — independent replication of ITSME's result
- Step 0 added to procedure: mandatory sector discovery via `grep -boa "Jz8PNRUF" rpmb_dump.bin`
- FAQ updated: Windows struct.error workaround (WSL2/Live USB), A/B slot divergence after OTA
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
