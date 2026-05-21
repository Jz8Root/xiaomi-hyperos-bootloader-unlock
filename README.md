# Xiaomi MTK Bootloader Unlock — HyperOS/MIUI14+ RPMB Bypass

**Affects:** All Xiaomi MTK devices with HyperOS/MIUI14+ and Kamakiri BROM access  
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

## The Method

The procedure depends on whether your specific LK binary implements the RPMB magic check.
**Don't assume — scan your LK first.** Two devices with the same codename and same SoC can
ship different LK builds with different lock implementations.

### Prerequisites

- [mtkclient](https://github.com/bkerler/mtkclient) with Kamakiri BROM exploit
- Access to BROM mode (see [Entering BROM Mode](#entering-brom-mode) below for the precise procedure)
- Quality USB DATA cable (not charge-only)
- **MANDATORY:** Full backup of NV partitions (commands below)


### Linux Pre-flight

On any modern Linux distro that ships with `ModemManager` and the `option` USB-serial driver
(Manjaro, Arch, Ubuntu, Fedora, openSUSE, etc.), mtkclient sessions silently fail with
`DaHandler - Please disconnect, start mtkclient and reconnect.` even though the udev rules
from `Setup/Linux/` are installed correctly.

The root cause is in `dmesg` immediately after the phone enters BROM:

```
usb 1-1: New USB device found, idVendor=0e8d, idProduct=0003
usb 1-1: GSM modem (1-port) converter now attached to ttyUSB0
```

The kernel's `option` driver (via `usb_wwan`/`usbserial`) claims the MediaTek port instantly on
enumeration and blocks libusb's `CLAIM_INTERFACE`. ModemManager grabs anything that looks like a
modem. mtkclient's udev rules grant userspace access but don't prevent kernel-driver binding.

**Run this before each mtkclient BROM session:**

```bash
sudo systemctl stop ModemManager
sudo modprobe -r option usb_wwan

# verify
lsmod | grep -E '^option|^usb_wwan' || echo "ok — modules unloaded"
systemctl is-active ModemManager   # should print: inactive
```

`usbserial` is built into the kernel on most distros — you don't need to (and can't) unload it.
Only `option` and `usb_wwan` matter.

The modules can auto-reload on udev events between sessions. If a later command fails with the
same `Please disconnect, start mtkclient and reconnect.` symptom, re-run the `modprobe -r` step.

When you're done with the unlock, restore the normal modem stack:

```bash
sudo systemctl start ModemManager
# option/usb_wwan will re-load automatically on next USB modem connect, or after reboot
```

### Entering BROM Mode

BROM is the boot-ROM USB-download mode that runs *before* the preloader. It only stays active if
the volume keys are held during its ~100 ms startup window — and that window is **before USB power
arrives**, not after. If you plug first and press keys after, BROM has already handed off to
preloader → LK, and the keys then trigger fastboot or recovery instead.

**The procedure that works reliably:**

1. **Phone fully off.** Not transitioning. Not in fastboot. Not displaying a logo. If unsure,
   hold Power for 15 s to force-off, then wait 5 s.
2. **USB unplugged.**
3. Press and hold **Vol+ AND Vol−** (both, simultaneously). On some devices Vol+ alone or
   Vol− alone works; try both keys first.
4. **While still holding the keys**, plug the USB cable in.
5. Keep holding **for 15+ seconds** after the cable is in.
6. Release.

**The screen must stay completely black throughout.** If you see anything — Xiaomi logo,
"FASTBOOT" text, the unlocked-warning screen, a vibration — the timing was wrong. Unplug,
force-off, retry.

> **mtkclient should already be running before you plug in.** Start `mtk.py r ...` /
> `mtk.py da rpmb r ...` / `mtk.py da seccfg unlock` first — it will print
> `Waiting for PreLoader VCOM, please reconnect mobile/iot device to brom mode` and sit there
> until USB enumeration happens. That way mtkclient grabs the device in the first ~100 ms after
> enumeration, before any kernel driver can race for the interface.

**Between every `da` command, the phone needs a fresh BROM entry.** Unplug, force-off if needed,
redo the key combo, replug.

Stuck phone in some intermediate MTK state (e.g. `0e8d:20ff` not recognised by mtkclient, or
fastboot wedged after a killed mtkclient run)? Two recovery paths:

- Hold Power 15 s to force-off, redo BROM from step 1.
- For a wedged USB endpoint without unplugging, reset the device node via ioctl:
  ```bash
  sudo python3 -c "import os, fcntl; fcntl.ioctl(os.open('/dev/bus/usb/BBB/DDD', os.O_WRONLY), 21780, 0)"
  ```
  (replace `BBB/DDD` with the bus/device numbers from `lsusb`).
  
### Step 0 — Mandatory backups

In BROM, dump everything that matters before any write operation:

```bash
# Critical partitions in one BROM session (sizes are mtkclient's uniform read, real content at the start)
python mtk.py r \
  nvdata,nvcfg,nvram,persist,protect1,protect2,seccfg,lk_a,lk_b,boot_a,boot_b \
  nvdata.bin,nvcfg.bin,nvram.bin,persist.bin,protect1.bin,protect2.bin,seccfg.bin,lk_a.bin,lk_b.bin,boot_a.bin,boot_b.bin

# RPMB (separate BROM session — phone must re-enter BROM between sessions)
python mtk.py da rpmb r rpmb_backup.bin
```

Without `nvdata` / `nvcfg` / `nvram` / `protect*` you risk "NV data corrupted" → bricked
IMEI and baseband. Keep these backups for months — they're your recovery path.

### Step 1 — Identify your LK with `scan_lk.py` ⟵ DECISION POINT

Run the scanner on the LK binary you just dumped:

```bash
python3 scan_lk.py lk_a.bin
```

The verdict drives which path you take:

| Verdict | Meaning | Path |
|-|-|-|
| `COMPATIBLE_FULL` | Magic `Jz8PNRUF` present in LK → `mi_check_magic()` is active | **Path A** below |
| `COMPATIBLE_SECCFG_ONLY` | Magic absent → LK falls back to seccfg unconditionally | **Path B** below |
| Other / `NOT_COMPATIBLE` | Investigate manually — share your `scan_lk.py --json` output in an issue | — |

> Older fleur units (and other "HyperOS-eligible" devices) ship the MIUI-13-era LK
> that Xiaomi never updated. On those, the RPMB lock layer simply isn't implemented
> and the destructive RPMB erase step is unnecessary. The scanner is the only
> reliable way to tell from outside.

### Path A — `COMPATIBLE_FULL` (RPMB magic present)

Three commands, one BROM cycle each:

```bash
# STEP A1: Erase RPMB magic region
python mtk.py da rpmb e --sector 57344 --sectors 4

# STEP A2: Unlock seccfg
python mtk.py da seccfg unlock
```

(Step 0 already produced the mandatory `rpmb_backup.bin`.) **Between every `da` command,
the phone needs a fresh BROM entry** — unplug, redo the key combo, replug.

If your device needs a specific preloader, add `--preloader preloader_CODENAME.bin` to each command.

**Note on the erase:** only 4 sectors at 57344 are touched — just the magic region. Lock-state length
(sector 57600) and signature data (sector 57856) are left untouched. Absent magic alone forces
the DEFAULT→seccfg fallback path.

**Non-Samsung UFS:** sector 57344 is the *Samsung* layout. Hynix and other UFS vendors may have
the magic at different offsets — see [RPMB Sector Reference](#rpmb-sector-reference) below. If
your dump's sector 57344 is empty AND `scan_lk.py` returned `COMPATIBLE_SECCFG_ONLY`, you don't
need to find the magic — skip to Path B.

### Path B — `COMPATIBLE_SECCFG_ONLY` (no RPMB magic — older LK)

One command:

```bash
python mtk.py da seccfg unlock
```

That's the entire write. No RPMB writes happen anywhere — the LK doesn't read the magic.
Look for these lines in the mtkclient output to confirm success:

```
XFlashExt - Detected V4 Lockstate
SecCfgV4 - hwtype found: V4
Sej - AES128 CBC - HACC init/run/terminate
DaHandler - Successfully wrote seccfg.
```

### Step 2 — Verify in fastboot

After mtkclient finishes, fully power-off the phone, then hold Vol- + plug USB to enter
fastboot. Run:

```bash
fastboot oem lks                 # Expected: (bootloader) lks = 0
fastboot getvar unlocked         # Expected: unlocked: yes
fastboot getvar secure           # Expected: secure: no
```

If `lks = 0`, the unlock is in seccfg and persistent.

### Step 3 — Clear the dm-verity state (REQUIRED on first boot after unlock)

If you boot to Android directly after unlock, you'll see Android's **"Your device is corrupt"**
dm-verity screen — that's actually proof the unlock took effect (a locked LK would have refused to hand
off to Android at all). The pre-existing userdata was written under the old trust state; wipe it before
the first Android boot:

```bash
fastboot erase userdata
fastboot erase metadata
fastboot reboot
```

Phone will boot into a fresh HyperOS setup wizard. Subsequent boots show the orange "unlocked"
warning for ~10 s — that's normal for an unlocked Xiaomi device.

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

## scan_lk.py — How the Scanner Works

The scanner that gates the procedure above analyzes any Xiaomi MTK LK binary using string
searches and byte pattern matching:

- Whether the RPMB magic string `Jz8PNRUF` is present in the binary (exact match)
- UFS RPMB type detection (heuristic based on constant values)
- RSA key detection (exact prefix match for the known Xiaomi key, entropy heuristic fallback)
- Function presence detection via string references — note: this is **string-based, not ARM instruction analysis**, so a Xiaomi build that strips or obfuscates debug strings could fool it
- Compatibility verdict with score (0-100%)

The scanner accepts LK binaries from any source:

```bash
# From firmware ZIP
unzip firmware.zip  # -> images/lk.img or lk_a.img

# From device via mtkclient (recommended — matches what's actually running)
python mtk.py r lk_a lk_a.bin

# Run scanner
python3 scan_lk.py lk_a.bin
python3 scan_lk.py lk_a.bin --json  # structured output
```

See [COMPATIBILITY.md](COMPATIBILITY.md) for the full device database — entries are indexed
by LK build hash because the same codename can ship multiple LK generations.

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
5. **HyperOS 1 PROVEN (Path A) + older MIUI/HyperOS LK builds PROVEN (Path B).** HyperOS 2/3 (2025+) have NOT been verified — run `scan_lk.py` first and report results.
6. Unlocking the bootloader voids manufacturer warranty.

## Credits

- [bkerler/mtkclient](https://github.com/bkerler/mtkclient) — the foundation that makes BROM access possible
- The Kamakiri exploit researchers
- Everyone who reported the seccfg bug on GitHub — your reports helped map the scope

## License

[AGPL-3.0](LICENSE) — If you use this code, you must publish your source code too. No closed-source paid tools.

---

Researched & tested by: **Jz8root**
