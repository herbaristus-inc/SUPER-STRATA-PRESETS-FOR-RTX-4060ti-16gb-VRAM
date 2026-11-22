# Boot environment — what the measurements actually ran on

This page documents the machine state behind the numbers. It is **not** a claim that every
reader needs the same boot setup, and it is **not** a driver-unlock tutorial.

## Measured environment

| Item | Value |
|---|---|
| GPU | NVIDIA GeForce RTX 4060 Ti 16 GB, device `10de:2805`, `ad102` |
| Boot | `nv-uefi-unlocker v2.1.8` (`physicsdolphin`, build TX) from a USB pendrive |
| Unlock proof | `loader.log`: `ss0=0x88888888`, `ss1=0x8`, `plm_open=true` |
| What the unlock changes | FP16/BF16/TF32 ~2×; **no** gain in INT8/dp4a/INT4/FP32 |
| VRAM OC | `nvidia-smi -lmc 10827`, applied at login by a Startup shortcut |
| Load clocks seen | SM 2865–2880 MHz, VRAM 10827 MHz, power limit 165 W |
| Display adapter | iGPU is primary; browsers/Electron/desktop apps pinned via `HKCU\Software\Microsoft\DirectX\UserGpuPreferences` `GpuPreference=1` |
| System RAM | **64 GB DDR5-6000 (XMP)** — required, not optional |

Without the unlocked boot, a previous session measured about **14% lower prefill**. The KV
cache is `int8` and the quantised experts do not benefit from the tensor-core unlock; the
difference comes from attention/draft-head work in FP16. Treat this as environment context,
not a portable promise.

## Why 64 GB DDR5 is a hard requirement

The 125B expert set lives in pinned host RAM; VRAM is a hot cache. At 1M context the `int8`
K/V alone takes 12.38 GiB of pinned RAM, on top of a ~37 GiB page-locked expert complement.
With 32 GB the model spills to the SSD tier and none of these figures are reachable.

## About the boot image

The pendrive image is **not included in this repository**. No ISO was available to ship at
the time of writing, and distributing a third-party unlocker image raises its own licensing
questions. If an image is published later it will be linked here with its SHA-256 and exact
version — never as an unverified binary.

## Reproducing without this exact boot

The presets are plain JSON and work on any Control 0.1.62 install. What will change is the
absolute speed. Report your own numbers with:

- engine and Control version,
- GPU model and VRAM clock,
- RAM size/speed,
- whether an unlocked boot was used,
- prompt length and reuse (fresh, nonce-unique prompts preferred).
