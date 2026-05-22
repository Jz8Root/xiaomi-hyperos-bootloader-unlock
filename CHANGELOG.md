# Changelog

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
