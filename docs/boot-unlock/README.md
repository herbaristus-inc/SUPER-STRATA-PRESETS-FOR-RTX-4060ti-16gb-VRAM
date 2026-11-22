# Boot pendrive — unlock payload

This folder is the **disaster-recovery copy** of the boot pendrive used for every measurement
in this repo. It is small: ~81 MB, not a 16 GB image.

## What it is

`nv-uefi-unlocker v2.1.8` (`physicsdolphin`, build TX) opens the PLL on the `ad102` GPU so
tensor cores run FP16/BF16/TF32 at roughly double rate. INT8/dp4a/INT4/FP32 are unaffected —
the gain here comes from attention and the draft head, not from the quantised experts.

Measured environment: `plm_open=true`, `ss0=0x88888888`, `ss1=0x8`, VRAM OC `10827`.
Without the unlocked boot, a previous session measured ~14% lower prefill.

## What is included

- `files/` — the exact payload: `EFI\BOOT\BOOTX64.EFI` and the eight root files.
- `SHA256SUMS.md` — hash and byte count of every file.
- `make_pendrive.ps1` — builds the pendrive from the payload.
- `MAKE-PENDRIVE.bat` — one-click launcher for the PowerShell script.

`loader.log` and `System Volume Information` are **not** included: one is machine-specific
boot state, the other is Windows metadata. Neither is needed to boot.

## Build a pendrive

1. Get the disk number:

   ```powershell
   Get-CimInstance Win32_DiskDrive | select Index,Model,Size,MediaType
   ```

2. Run `MAKE-PENDRIVE.bat` and type the number. The script refuses any disk whose media type
   is not `Removable`, prints model and size, and requires you to type `ERASE`.

3. It runs `diskpart` on **that disk only**: clean, one primary active FAT32 partition labelled
   `UNLOCK`, then copies the payload and verifies every file by SHA-256.

4. Boot from the pendrive. At the banner, press **SPACE** or **ENTER** to confirm. Any other
   key, or 30 seconds with no key, aborts and unlocks nothing. Then boot Windows again.

5. Confirm `plm_open=true` in `G:\loader.log` (or whatever letter the pendrive gets).

If you want the optional 5-second auto-run marker, create an empty
`i_know_what_i_am_doing.txt` at the root of the pendrive. It is not included on purpose:
auto-run is not something to bake into a recovery image.

## Scope and safety

This is a vendor-specific firmware unlock for one GPU family. It is provided as-is, with no
warranty, and may be unsupported by the GPU vendor. It is **not required** to run the presets;
it only changes the absolute speed. Keep the original pendrive if you have it — this folder
is a rebuild path, not a replacement for the vendor tool.
