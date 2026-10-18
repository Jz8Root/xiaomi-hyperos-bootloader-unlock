# Verification Evidence

## 1. Magic String in LK Binary (Xiaomi-signed firmware)

The magic string is hardcoded in the LK bootloader binary from official HyperOS firmware.

**Source firmware:** HyperOS OS1.0.11.0.TKEEUXM (Android 13 EEA)
**File:** lk_a.img extracted from official firmware ZIP
**Offset:** 0x110608

```
$ xxd -s 0x110608 -l 32 lk_a.img
00110608: 4a7a 3850 4e52 5546 0000 0000 6f70 6572  Jz8PNRUF....oper
00110618: 6174 696f 6e20 6661 696c 6564 206f 7220  ation failed or 
```

The author's handle (Jz8root) derives from this firmware constant discovered during
reverse engineering — not the other way around. Anyone can verify by downloading the
official fleur HyperOS firmware and running `xxd -s 0x110608 -l 8 lk_a.img`.

**How to reproduce:**
1. Download firmware from https://github.com/XiaomiFirmwareUpdaterReleases/firmware_xiaomi_fleur
2. Extract: `unzip firmware.zip` → `images/lk_a.img`
3. Verify: `xxd -s 0x110608 -l 8 lk_a.img`
4. Expected: `4a7a 3850 4e52 5546` = "Jz8PNRUF"

## 2. Decompiled LK Code — mi_check_magic (FUN_0003b848)

Ghidra decompilation of the function that checks the RPMB magic:

```c
int mi_check_magic(void) {    // FUN_0003b848
  int rpmb_type = rpmb_get_type();    // FUN_0006e968
  ushort offset;

  if (rpmb_type == 0x1000000) {       // Alt UFS type
    offset = 0xe000;
  } else if (rpmb_type == 0x400000) { // UFS 4 MiB layout (all confirmed Tier 1 devices)
    offset = 0x3fe0;
  } else {
    return 7;                          // Unknown type → error
  }

  char buf[8];
  int rc = rpmb_read(offset, buf, 8); // FUN_0003b61c — reads 8 bytes from RPMB
  if (rc == 0) {
    if (memcmp(buf, "Jz8PNRUF", 8) == 0) {  // FUN_0003fc24
      return 0;  // magic PRESENT
    }
    return 3;    // magic ABSENT
  }
  return rc;     // error
}
```

**What this proves:**
- The LK reads 8 bytes from RPMB block address 0x3FE0 (UFS 4 MiB path, type 0x400000)
- It compares them against the hardcoded constant "Jz8PNRUF" at offset 0x110608 in the LK binary
- Return 0 = magic present (RPMB overrides seccfg → LOCKED)
- Return 3 = magic absent (fallback to seccfg → UNLOCK if seccfg says so)

## 3. RPMB Dumps — Before and After Unlock

mtkclient `da rpmb r` produces a **32 MB** (0x2000000) dump. This is mtkclient's
dump format — larger than the actual 4 MB RPMB partition (type 0x400000).

### Before unlock (magic present)

**SHA256:** `d19401c42989a161007433e8625676232b8b359dfaa664b59d6fb0318474ed41`

```
$ xxd -s 0xE00000 -l 16 rpmb_backup_before_unlock.bin
00e00000: 4a7a 3850 4e52 5546 0000 0000 0000 0000  Jz8PNRUF........
```

### After unlock (magic erased)

**SHA256:** `b58060882c5bfd502ea1a75e7eb7ccc886546a51ce91e6d6594bfbec44ca3e2e`

```
$ xxd -s 0xE00000 -l 16 rpmb_after_unlock.bin
00e00000: 0000 0000 0000 0000 0000 0000 0000 0000  ................
```

### Fresh dump (2026-05-16, post-unlock, persistent)

New dump taken months after the original unlock. Magic still absent — confirming
the erase is persistent across reboots and time.

```
$ ls -l rpmb_fresh.bin
33554432 bytes (32 MB) — same mtkclient dump format
$ python3 -c "d=open('rpmb_fresh.bin','rb').read(); print('Jz8PNRUF' if b'Jz8PNRUF' in d else 'NOT FOUND')"
NOT FOUND
```

## 4. Address Mapping

### What is proven

| Fact | Source | Status |
|------|--------|--------|
| LK reads magic from RPMB block 0x3FE0 (Samsung) | Ghidra decompilation FUN_0003b848 | **PROVEN** |
| "Jz8PNRUF" constant at LK offset 0x110608 | xxd on official firmware lk_a.img | **PROVEN** |
| `da rpmb e --sector 57344 --sectors 4` erases the magic | before/after dumps + hardware unlock | **PROVEN** |
| Unlock is persistent across reboots | fresh dump 2026-05-16, months later | **PROVEN** |
| mtkclient dump is 32 MB (not 4 MB RPMB size) | three independent dumps, all 0x2000000 | **PROVEN** |
| Magic at byte 0xE00000 in mtkclient dump space | xxd on before-unlock dump | **PROVEN** |
| Sector 57344 = 0xE00000 / 256 in mtkclient addressing | math | **PROVEN** |

### Why the dump is 32 MB (mtkclient source code audit)

Source: `mtkclient/Library/DA/xflash/extension/xflash.py`, function `read_rpmb()`:

```python
# Line 664-665: UFS dump size is hardcoded
elif self.mtk.daloader.daconfig.storage.flashtype == "ufs":
    sectors = (512 * 256)  # = 131072 sectors × 256 bytes = 32 MB
```

mtkclient hardcodes **512 × 256 = 131072 sectors** for UFS RPMB reads, regardless
of the actual RPMB partition size (4 MB for Samsung type 0x400000). This explains
the 32 MB dump — it reads the entire addressable RPMB space, not just the used portion.

The sector is passed **directly** to the Download Agent hardware with no conversion:

```python
# Line 470-475: custom_rpmb_read passes sector as-is
def custom_rpmb_read(self, sector, sectors):
    cmd = XCmd.CUSTOM_RPMB_READ
    if self.cmd(cmd):
        self.xsend(sector)     # sector sent directly to DA → hardware
        self.xsend(sectors)    # no address translation in Python layer
```

**Conclusion:** mtkclient sector numbers = hardware RPMB sector numbers. No mapping,
no conversion. Sector 57344 in mtkclient = sector 57344 on the physical RPMB.

### LK-side addressing (0x3FE0)

The LK and mtkclient use different abstraction layers to address the same RPMB cells:

- **mtkclient** passes sector numbers directly to hardware (confirmed above). Sector
  57344 = hardware sector 57344. The erase at sector 57344 removes the magic and
  triggers the unlock. This is the user-facing value.
- **The LK** uses its own internal offset 0x3FE0, passed to `rpmb_read()` (FUN_0003b61c),
  which is translated to a JEDEC RPMB data frame address by the hardware driver
  (FUN_000707b4). The driver handles the conversion between the LK's abstract
  offset and the physical RPMB sector — standard practice in embedded RPMB
  implementations where the driver manages frame construction and sector mapping.

Both stacks ultimately address the same 8-byte magic cell. The LK decompilation
confirms *what* is read (magic at offset 0x3FE0, compared against "Jz8PNRUF").
The mtkclient source confirms *how* users erase it (sector 57344, passed directly
to hardware). The before/after dumps confirm *that it works*.

> Technical note: 0x3FE0 from the Ghidra decompilation of the UFS 4 MiB path
> (type 0x400000) in mi_check_magic. Interpreted as a 256-byte block index:
> 0x3FE0 x 256 = 0x3FE000 = 4,186,112 bytes -- 8 KB from the end of a 4 MB RPMB
> (0x400000 = 4,194,304). Consistent with a reserved metadata region at the tail
> of the RPMB partition.

## 5. Additional Findings (October 2026)

### MT6833 sector depends on LK driver family, not SoC alone

ogmkp (POCO M4 5G `thunder`, MT6833 Dimensity 700, [#18](https://github.com/Jz8Root/xiaomi-hyperos-bootloader-unlock/issues/18)) decompiled the `light` LK driver and found the divergence with `gold`:

- LK `0x34C2C`: selects internal base, two UFS capacity cases produce `0x003FE000` or `0x00FFE000`
- LK `0x6AD96`: `uxth r3, r6` truncates the starting RPMB address to 16 bits before constructing the request
- Result: `0x003FE000 & 0xFFFF = 0xE000` and `0x00FFE000 & 0xFFFF = 0xE000`, both map to sector 57344

The `gold` driver (Dimensity 6080, Redmi Note 13 5G) does not perform this truncation and maps to sector 65504.

| LK family | SoC marketing | Sector | Dump offset | Status |
|-|-|-|-|-|
| gold | Dimensity 6080 | 65504 | `0xFFE000` | Tier 1 (KTS618, Gkhupo) |
| light | Dimensity 700 | 57344 | `0xE00000` | Tier 1 (ogmkp) |

### Preloader magic restoration on Tier 3b devices

LucaCraft89 (rubypro, MT6877, SK Hynix UFS, [#13](https://github.com/Jz8Root/xiaomi-hyperos-bootloader-unlock/issues/13)) performed a three-dump sequence that proved the preloader is the restorer:

1. After erase + cold BROM re-entry: magic **absent** (erase persists in flash)
2. After any boot path (even just reaching the Mi logo): magic **present** (preloader restores it)
3. The `0xAA` marker test: 248 bytes of a 256-byte sector persisted across cold cycle, only the 8 magic bytes reverted to `Jz8PNRUF`

Both LucaCraft89 and burg1ar (pissarrro, MT6877, Samsung UFS, [#11](https://github.com/Jz8Root/xiaomi-hyperos-bootloader-unlock/issues/11)) ran the full `erase -> reset -> seccfg unlock -> reset -> fastboot` sequence and obtained `unlocked: no` -- confirming the preloader restoration survives the complete procedure.

vivaad (earth, Redmi 12C, MT6769Z eMMC, [#8](https://github.com/Jz8Root/xiaomi-hyperos-bootloader-unlock/issues/8)) reproduced the same pattern on a different SoC and storage type, and added one new finding: the preloader boot1 partition dump does **not** contain the literal string `Jz8PNRUF`. The restorer either computes the value or resides in a flash region outside the boot1 dump.
