# Changelog

## 2026-06-16 — v2.0.0: 6 Devices, 4 SoCs, Full HyperOS Lifecycle
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
