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

Starting with HyperOS, Xiaomi stores a magic string in the **RPMB** (Replay Protected Memory Block). The LK reads it before falling back to seccfg — when present, RPMB overrides seccfg even if seccfg says UNLOCK.


**The fix:** erase the RPMB magic. This forces the LK to fall back to seccfg, which mtkclient can freely write to UNLOCK.

**Why it persists across reboots:** when the magic is absent AND seccfg = UNLOCK, the LK does NOT rewrite the magic. The code path that restores the magic only triggers when seccfg != UNLOCK. This behavior is inferred from the Ghidra decompilation of `mi_get_lock_state()` and confirmed empirically: RPMB dumps taken after multiple reboots show the magic region remains zeroed. See [proof/VERIFICATION.md](proof/VERIFICATION.md) for dump evidence.

![mi_check_magic() boot flow](assets/mi_check_magic_flow.png)

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
- **A USB 2.0 port.** Not USB 3.0. See below, this one silently ruins runs.
- **MANDATORY:** Full backup of NV partitions (commands below)

### Use a USB 2.0 port, never USB 3.0

On this chipset family, RPMB and seccfg writes over a USB 3.0 controller get acknowledged by
mtkclient's protocol layer and **never physically commit to flash**. The tool prints
`Successfully wrote seccfg`, the operation looks perfect, and nothing has changed on the device.

The signature is unmistakable once you know it: every command reports success, and every flag is
exactly as it was before you started.

```
fastboot oem lks           -> lks = 1        unchanged
fastboot getvar unlocked   -> unlocked: no   unchanged
fastboot getvar secure     -> secure: yes    unchanged
```

Diagnosed on earth/MT6769Z in [#8][i8], where the reporter had switched to the blue port without
realising. Use the **black** USB 2.0 port, front or back, and prefer a direct connection over a hub.

Two traps worth knowing:

- some laptops have a physically black port that is **internally wired to the xHCI 3.0
  controller** anyway, through sloppy board routing. If a second attempt on the same port fails
  the same silent way, try a different port, a USB 2.0 hub, or another machine entirely
- USB-C ports are almost always 3.x. Prefer a USB-A 2.0 port with an A-to-C cable

**Always verify by re-reading the RPMB, never by trusting the log line:**

```bash
python mtk.py da rpmb r rpmb_check.bin
grep -boa "Jz8PNRUF" rpmb_check.bin
```


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
   hold Power for 15 s to force-off, then wait 5 s. This is fine **before** you start, but once
   the RPMB is erased the Power button is off limits, see
   [the rule below](#never-use-the-power-button-between-the-rpmb-erase-and-seccfg-unlock).
2. **USB unplugged.**
3. Press and hold **Vol+ AND Vol−** (both, simultaneously). On some devices Vol+ alone or
   Vol− alone works; try both keys first.
4. **While still holding the keys**, plug the USB cable in.
5. Keep holding **for 15+ seconds** after the cable is in.
6. Release.

**The screen must stay completely black throughout.** If you see anything — Xiaomi logo,
"FASTBOOT" text, the unlocked-warning screen, a vibration — the timing was wrong. Unplug,
force-off, retry.

**If this happens after an RPMB erase**, the preloader has already run and has restored the magic.
Re-dump to confirm, redo the erase, and retry the BROM entry using only the volume keys. See
[the rule below](#never-use-the-power-button-between-the-rpmb-erase-and-seccfg-unlock).

> **mtkclient should already be running before you plug in.** Start `mtk.py r ...` /
> `mtk.py da rpmb r ...` / `mtk.py da seccfg unlock` first — it will print
> `Waiting for PreLoader VCOM, please reconnect mobile/iot device to brom mode` and sit there
> until USB enumeration happens. That way mtkclient grabs the device in the first ~100 ms after
> enumeration, before any kernel driver can race for the interface.

**Between every `da` command, the phone needs a fresh BROM entry.** Unplug, redo the key combo,
replug.

#### Never use the Power button between the RPMB erase and seccfg unlock

🚨 This is the single most important rule in this document, and it is the reason most reported
failures fail.

**The preloader rewrites the RPMB magic on every start-up.** Not LK, not HyperOS. The preloader.
Reaching the Mi logo is enough. So anything that starts the phone between your erase and your
unlock silently undoes the erase, and nothing tells you.

Re-entering BROM does **not** start the phone, so it is safe:

| Action | Safe? | Why |
|-|-|-|
| unplug, hold Vol+ and Vol-, replug | ✅ | BROM only, the preloader never runs |
| Power button to shut down or restart | ❌ | preloader runs, magic is rewritten |
| letting the Mi logo appear at all | ❌ | preloader has already run |
| `fastboot reboot` | ❌ | same |

So the erase and the unlock are two ordinary BROM sessions, with a normal unplug and key-combo
in between. Nothing exotic is required:

```bash
python mtk.py da rpmb e --sector <YOUR_SECTOR> --sectors 4
#   unplug, hold Vol+ and Vol-, replug. Do not touch the Power button.
python mtk.py da seccfg unlock
```

**How this was established.** LucaCraft89 ([#13][i13]) ran three dumps on rubypro/MT6877. After the
erase and a full cold BROM re-entry with Kamakiri re-run and the DA re-uploaded, the magic was
**gone**. He then powered the phone off with the buttons, re-read, and the magic was **back**. He
also confirmed it returns when the phone only reaches the Mi logo, which is what pins the
responsibility on the preloader rather than on LK.

**Why the phone sometimes ends up in a strange state:** after `da rpmb e` completes, mtkclient
calls neither `close()` nor `shutdown()`. The command returns and leaves the device with the DA
still running and still powered. On some units the Power button then reboots instead of shutting
down, which is how katavnnn ([#12][i12]) first ran into this on sea/MT6781.

##### If the phone gets stuck and you need to reset it

Stuck in an intermediate MTK state (e.g. `0e8d:20ff` not recognised by mtkclient, or fastboot
wedged after a killed mtkclient run)? Three options, least invasive first. **None of them are
needed in the normal flow** where you simply unplug and redo the key combo.

- **Reset the USB endpoint without unplugging**, which does not touch the phone's power state:
  ```bash
  sudo python3 -c "import os, fcntl; fcntl.ioctl(os.open('/dev/bus/usb/BBB/DDD', os.O_WRONLY), 21780, 0)"
  ```
  (replace `BBB/DDD` with the bus/device numbers from `lsusb`).
- **`python mtk.py reset`** issues a DA shutdown with `bootmode=0`. It works on some units and
  fails on others with `DeviceClass - [Errno 2] Entity not found`, and note that the
  `Reset command was sent` message is printed unconditionally by mtkclient whether or not the
  command actually went through, so it is not a confirmation.
- **Disconnect the battery connector** from the board, reconnect, then hold Vol+ and Vol- before
  inserting the cable. Proven on hardware by katavnnn ([#12][i12]) and it cannot start the phone
  by accident, but it means opening the back cover. Last resort.
  
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

**Scan both slots — they can differ.** After an OTA update, slot A and slot B can carry different LK builds. Confirmed on Redmi 12 (fire, HyperOS 2.0): lk_a = COMPATIBLE_SECCFG_ONLY, lk_b = COMPATIBLE_FULL. The device boots on the active slot — use that result.

```bash
python3 scan_lk.py lk_a.bin
python3 scan_lk.py lk_b.bin
# Use the result matching your active slot (check: fastboot getvar current-slot)
```

The verdict drives which path you take:

| Verdict | Meaning | Path |
|-|-|-|
| `COMPATIBLE_FULL` | Magic `Jz8PNRUF` present in LK → `mi_check_magic()` is active | **Path A** below |
| `COMPATIBLE_SECCFG_ONLY` | Magic absent → LK falls back to seccfg unconditionally | **Path B** below |
| `MAYBE` / `UNKNOWN` | Not enough evidence to classify. Investigate manually, and share your `scan_lk.py --json` output in an issue | neither |

> **Do not read the Path B score as a confidence level.** A `COMPATIBLE_SECCFG_ONLY` verdict
> tops out at **44/100 by construction**, because 47 of the 100 points are the magic string
> that a Path B device does not have, and the `mi_check_magic` check keys off that same
> string. A 31/100 Path B verdict is not a weak result: the absent magic *is* the finding.
> Only Path A verdicts should be read against the 0-100 scale.

> Older fleur units (and other "HyperOS-eligible" devices) ship the MIUI-13-era LK
> that Xiaomi never updated. On those, the RPMB lock layer simply isn't implemented
> and the destructive RPMB erase step is unnecessary. The scanner is the only
> reliable way to tell from outside.

### Path A — `COMPATIBLE_FULL` (RPMB magic present)

Three commands, one BROM cycle each:

**⚠️ Before erasing: locate your RPMB magic sector first** — it is SoC-specific.
Dump your RPMB and grep for the magic string:

```bash
python3 mtk.py da rpmb r rpmb_dump.bin
grep -boa "Jz8PNRUF" rpmb_dump.bin
# byte_offset / 256 = your sector
# MT6781/MT6769Z → 57344  |  MT6833 → 65504  |  unknown SoC → use grep result
```

**If grep returns more than one offset, they are not separate copies.** The dump mtkclient
produces is larger than the physical RPMB, so the same location shows up several times. Hits
separated by exactly 16 MiB (`0x1000000`) are aliases of each other, because the address field in
an RPMB frame is two bytes and therefore wraps at 65536 sectors:

```
122880 mod 65536 = 57344      same physical location, seen twice
```

Erase the **lowest** offset of each aliased pair, once. On rubypro, grep returns `14680064` and
`31457280`, which is sector 57344 and its 16 MiB alias, so only 57344 gets erased. On miel it
returned four hits collapsing to two real locations (16352 and 57344), and 57344 alone was
sufficient.

Then erase the sector you found:

```bash
# STEP A1: Erase RPMB magic region (replace <YOUR_SECTOR> with grep result above)
python mtk.py da rpmb e --sector <YOUR_SECTOR> --sectors 4

# STEP A2: Unlock seccfg
python mtk.py da seccfg unlock
```

(Step 0 already produced the mandatory `rpmb_backup.bin`.) **Between every `da` command,
the phone needs a fresh BROM entry**: unplug, redo the key combo, replug.

**A1 and A2 are the critical pair.** If the phone boots between them, the magic can come back, and
A2 then unlocks a seccfg that the restored magic will override on the next boot. **Never touch the
Power button in this window.** Unplug and redo the key combo, that is all that is needed. See
[the rule above](#never-use-the-power-button-between-the-rpmb-erase-and-seccfg-unlock).

If your device needs a specific preloader, add `--preloader preloader_CODENAME.bin` to each command.

**Note on the erase:** only 4 sectors are touched — just the magic region. Absent magic alone forces
the DEFAULT→seccfg fallback path.

#### If you re-dump to check the erase, do it in a separate cold session

⚠️ A `da rpmb r` issued without a full power cycle in between can reattach to the still-live DA
session and return a **volatile view** in which the magic already looks erased, whether or not
anything reached the flash. That is a false positive, and it is convincing enough to make you
believe the erase worked when it did not.

```bash
# WRONG: chained read, may show a magic that is not actually gone
python mtk.py da rpmb e --sector <YOUR_SECTOR> --sectors 4
python mtk.py da rpmb r rpmb_check.bin

# RIGHT: power cycle, fresh BROM entry, then read
python mtk.py da rpmb e --sector <YOUR_SECTOR> --sectors 4
#   ... power the phone down completely, re-enter BROM ...
python mtk.py da rpmb r rpmb_check.bin
grep -boa "Jz8PNRUF" rpmb_check.bin
```

Discovered by LucaCraft89 ([#13][i13]) while investigating an erase that reported success and did not
persist. Three dumps were needed to see it: cold baseline, same-session read, and cold read after
a power cycle. Only the third one tells you the truth.

**Reading the signature field is a better check than the magic.** If the record at `0xE20000`
contains `wrong unlock data` instead of `milock state`, the boot chain has flagged the record as
tampered, which means it ran and inspected the RPMB. That distinguishes "erased then restored"
from "never erased", which magic presence alone cannot. Observed by LucaCraft89 ([#13][i13]).

**Storage vendor does not change the sector.** An earlier version of this document said sector
57344 was "the Samsung layout" and that Hynix parts might place the magic elsewhere. That turned
out to be wrong: rubypro carries SK Hynix `H9QT1G6DN6X132` and its magic sits at exactly the same
offset, confirmed by grep in [#13][i13]. What does move the sector is the **SoC**, not the storage
part. MT6781 and MT6769Z use 57344, MT6833 uses 65504.

If your dump has no magic at all AND `scan_lk.py` returned `COMPATIBLE_SECCFG_ONLY`, you do not
need to find it, skip to Path B.

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
fastboot getvar unlocked         # AUTHORITATIVE. Expected: unlocked: yes
fastboot getvar secure           # Expected: secure: no
fastboot oem lks                 # Optional. Expected: (bootloader) lks = 0
```

**`fastboot getvar unlocked` is the source of truth.** If it returns `yes`, the unlock is in
seccfg and persistent. Stop there, you are done.

`oem lks` is a hidden OEM command that not every LK build implements. On builds that don't, it
returns an error while the device is perfectly unlocked:

```
fastboot oem lks
FAILED (remote: Unable to do OEM command Status(-7, EX_UNSUPPORTED_OPERATION)

fastboot getvar unlocked
unlocked: yes
```

Reported on sea/MT6781 by katavnnn ([#12][i12]). Treat `oem lks` as a bonus signal, never as the
verification step. An error there means the command is missing, not that the unlock failed.

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

<details>
<summary><strong>RPMB Sector Reference</strong> (click to expand)</summary>

### Proven: POCO M4 Pro 4G (fleur, Samsung UFS)

Verified by RPMB dump analysis. See [proof/VERIFICATION.md](proof/VERIFICATION.md) for full evidence.

| Data | Dump Byte Offset | mtkclient Sector | Content |
|------|-----------------|-----------------|---------|
| Lock magic | **0xE00000** | **57344** | `Jz8PNRUF`, 8 bytes |
| Lock state length | 0xE10000 | 57600 | length of the string at 0xE20000 |
| Signature data | 0xE20000 | 57856 | `milock state`, or `wrong unlock data` after tampering |

Sector math: `byte_offset / 256 = sector` → `0xE00000 / 0x100 = 57344`

Command: `da rpmb e --sector 57344 --sectors 4`

> **`0xE10000` is a length field, not a counter.** It holds the length of the string stored at
> `0xE20000`, and it is easy to misread as a write counter. On rubypro it was seen going from
> `0x0C` to `0x11` alongside the string changing from `milock state` (12 characters) to
> `wrong unlock data` (17 characters). Both fields are updated together by the boot chain, so a
> change there means something inspected the record, not that a write was authenticated. The real
> RPMB write counter is not in the addressable data area at all, it is a controller register
> returned inside the response frame.

> **Note:** The LK code internally uses offset 0x3FE0 when calling `rpmb_read()`. The mapping
> from this LK-internal address to the physical dump offset 0xE00000 is handled by the RPMB
> driver. For users, only the mtkclient sector number matters.

### Other SoCs

The sector is **SoC-specific, not storage-vendor-specific**. rubypro carries SK Hynix
`H9QT1G6DN6X132` and has its magic at 57344 like the Samsung MT6781 parts, so do not go looking
for a different offset just because your UFS is not Samsung.

Known values:

| SoC | Sector | Dump offset | Confirmed by |
|-|-|-|-|
| MT6781 (Helio G96) | 57344 | `0xE00000` | fleur, miel, sea |
| MT6769Z (Helio G85) | 57344 | `0xE00000` | fire |
| MT6833 (Dimensity 6080) | 65504 | `0xFFE000` | gold, found by KTS618 |
| MT6877 (Dimensity 920/1080) | 57344 | `0xE00000` | rubypro |

If your SoC is not listed, dump the RPMB and grep. And read the note on multiple hits above:
offsets exactly 16 MiB apart are aliases of one location, not separate copies.

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

# Run scanner — scan BOTH slots (lk_a and lk_b can differ after OTA)
python3 scan_lk.py lk_a.bin
python3 scan_lk.py lk_b.bin
# Use the result matching your active slot (fastboot getvar current-slot)
python3 scan_lk.py lk_a.bin --json  # structured output
```

See [COMPATIBILITY.md](COMPATIBILITY.md) for the full device database — entries are indexed
by LK build hash because the same codename can ship multiple LK generations.

</details>

<details>
<summary><strong>FAQ</strong> (click to expand)</summary>



**Q: How can you erase RPMB without the device-specific RPMB key?**  
A: mtkclient derives the RPMB authentication key via the HACC engine through SEJ after the Kamakiri BROM exploit — the same mechanism it uses to handle SecCfgV4 encryption. The key derivation happens transparently when you run the `da rpmb e` command.

**Q: Will this wipe my data?**  
A: Yes. Unlocking the bootloader triggers a factory reset on first boot. Back up everything.

**Q: Can I relock after?**  
A: Yes. `mtk da seccfg lock` relocks. Full lock/unlock cycle tested and reversible.

**Q: Why erase only 4 sectors?**  
A: We only need to remove the magic string. The lock state length and signature data at higher sectors are irrelevant once the magic is absent — the LK falls back to seccfg without reading them.

**Q: Every command said success but nothing is unlocked. What happened?**  
A: Two known causes, both silent, and both print a perfect log.

1. **You were on a USB 3.0 port.** Writes get acknowledged but never reach flash. Move to a black USB 2.0 port and redo the whole procedure. See [Use a USB 2.0 port](#use-a-usb-20-port-never-usb-30).
2. **The phone started up between the erase and the unlock.** The preloader rewrites the magic on any start-up, and the Mi logo alone is enough. Never use the Power button in that window. See [the rule](#never-use-the-power-button-between-the-rpmb-erase-and-seccfg-unlock).

Diagnose by re-reading rather than by reading logs: dump the RPMB in a fresh BROM session and `grep -boa "Jz8PNRUF"`. If the magic is present, the erase did not survive. If the record at `0xE20000` reads `wrong unlock data` instead of `milock state`, the boot chain ran and reverted you.

**Q: `fastboot oem lks` returns an error. Did it fail?**  
A: Not necessarily. That OEM command is not implemented on every LK build. On sea/MT6781 it returns `EX_UNSUPPORTED_OPERATION` while the device is genuinely unlocked. `fastboot getvar unlocked` is the authoritative check.

</details>

## Warnings

1. **BACKUP RPMB FIRST.** Step 1 is your safety net. Never skip it.
2. **BACKUP NV PARTITIONS** (nvdata, nvcfg, nvram, persist, protect1, protect2) — without these, you risk "NV data corrupted" which breaks IMEI and baseband.
3. **THIS WILL WIPE YOUR DATA.** Factory reset on first boot after unlock.
4. **NEVER TOUCH THE POWER BUTTON** between the RPMB erase and `seccfg unlock`. The preloader
   rewrites the magic on any start-up, and reaching the Mi logo is enough. See
   [the rule](#never-use-the-power-button-between-the-rpmb-erase-and-seccfg-unlock).
5. **USB 2.0 ONLY.** A USB 3.0 controller makes writes report success without committing to flash.
   See [Use a USB 2.0 port](#use-a-usb-20-port-never-usb-30).
6. **BROM V6 = NO GO,** but do not read that as a number comparison. MediaTek part numbers are not
   chronological: MT6877 is a 2021 part, older than the 2022 MT6789, and Kamakiri runs on it. The
   patched parts are MT6789, MT6855 and later designs. See [COMPATIBILITY.md](COMPATIBILITY.md).
7. **HyperOS 1, 2, and 3 all CONFIRMED.** Method holds across the full HyperOS lifecycle. Always run `scan_lk.py` on both lk_a and lk_b first.
8. **SCAN BOTH LK SLOTS.** lk_a and lk_b can carry different LK builds after an OTA. Confirmed on Redmi 12 (fire, HyperOS 2.0) — slot B had the RPMB lock, slot A didn't.
9. **VERIFY BY RE-READING, NOT BY READING LOGS.** Both failure modes above print success. Only a
   fresh RPMB dump and `fastboot getvar unlocked` tell you the truth.
10. Unlocking the bootloader voids manufacturer warranty.

## Credits

- [bkerler/mtkclient](https://github.com/bkerler/mtkclient) — the foundation that makes BROM access possible
- The Kamakiri exploit researchers
- Everyone who reported the seccfg bug on GitHub — your reports helped map the scope

## License

[AGPL-3.0](LICENSE) — If you use this code, you must publish your source code too. No closed-source paid tools.

---

Researched & tested by: **Jz8root**

[i8]: https://github.com/Jz8Root/xiaomi-hyperos-bootloader-unlock/issues/8
[i12]: https://github.com/Jz8Root/xiaomi-hyperos-bootloader-unlock/issues/12
[i13]: https://github.com/Jz8Root/xiaomi-hyperos-bootloader-unlock/issues/13
