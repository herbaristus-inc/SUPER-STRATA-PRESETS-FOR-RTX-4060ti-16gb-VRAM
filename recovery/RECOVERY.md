# Recovery — from a clean Windows install to the measured setup

This is the "save the harvest" path. If the machine is lost, clone this repo first, then work
through the steps in order. Each step has a verification command. An agent with shell access
can run the whole checklist; a human can follow it by hand.

**Nothing here downloads model weights automatically** — those are ~84 GB from Hugging Face and
need their own storage decision. Everything else is reproducible from this repo.

## Step 0 — clone and verify the repo

```powershell
git clone <THIS_REPO_URL>
cd SUPER-STRATA-PRESETS-FOR-RTX-4060ti-16gb-VRAM
git log -1 --oneline
.\verify.ps1
```

`verify.ps1` checks the payload hashes, the preset invariants and that the renderer works.

## Step 1 — Windows baseline

- Windows 11, UEFI mode, Secure Boot as shipped.
- iGPU as the primary display adapter. Pin browsers/Electron/desktop apps to it with
  `HKCU\Software\Microsoft\DirectX\UserGpuPreferences` → `GpuPreference=1` so the 4060 Ti's
  VRAM stays available to Strata.
- Re-enable the XMP profile in BIOS: **DDR5-6000**. JEDEC 4800 is not the measured machine.
- VRAM OC at login: `nvidia-smi -lmc 10827`. Verify under load: SM 2865–2880 MHz,
  VRAM 10827 MHz, power limit 165 W. 198 W buys nothing.

## Step 2 — boot pendrive

If the original pendrive is gone:

```powershell
Get-CimInstance Win32_DiskDrive | select Index,Model,Size,MediaType
.\boot-unlock\MAKE-PENDRIVE.bat
```

Type the disk number of a removable USB drive. It will be erased. Reboot from it, press SPACE
at the unlocker banner, boot Windows again, and confirm `plm_open=true` in the pendrive log.
See [`boot-unlock/README.md`](../boot-unlock/README.md).

## Step 3 — runtime prerequisites

- **Python 3.12** with the NVIDIA CUDA 13 runtime (`nvidia/cu13/bin/x86_64` in site-packages).
- **Strata engine and Control, both 0.1.62**. Other versions have different prefill env vars.
- **NVIDIA driver** compatible with CUDA 13.

Verify:

```powershell
python --version
python -c "import nvidia; print('cu13 ok')"
```

## Step 4 — model and draft pack

Download from
<https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF>:

- `IQ3_S/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf` (shard 1, ~54.8 GB)
- `IQ3_S/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00002-of-00002.gguf` (n-gram shard, ~28.8 GB)
- `mmproj-Qwen3.8-Flash-Next-BF16.gguf` (vision, ~0.91 GB)

Plus the matched DFlash2 draft pack `qwen3.8-flash-next-dflash2.strata1.q4_0-selq4.pack` and its
`draft_vocab.bin`, and the experimental-speed-projection GGUF used by `--control-vector-scaled`.
See [`MODEL.md`](../MODEL.md) for why this quant and not another.

**64 GB DDR5 is required.** 1M K/V at `int8` is 12.38 GiB pinned, on top of a ~37 GiB
page-locked expert arena. On 32 GB the weights spill to SSD and none of these numbers happen.

## Step 5 — render and launch the presets

```powershell
set STRATA_ROOT=C:\path\to\strata
set STRATA_DATA=C:\path\to\Strata-data
set PYTHON=C:\path\to\python.exe
python tools\render_preset.py presets\strata-512k-routed.json.template ^
  --strata-root "%STRATA_ROOT%" --strata-data "%STRATA_DATA%" ^
  --python "%PYTHON%" --out "%STRATA_ROOT%\strata-512k-routed.json"
python tools\render_preset.py presets\strata-1m-h4.json.template ^
  --strata-root "%STRATA_ROOT%" --strata-data "%STRATA_DATA%" ^
  --python "%PYTHON%" --out "%STRATA_ROOT%\strata-1m-h4.json"
```

Then copy the two `.bat` templates from `launchers/` into `STRATA_ROOT`, start the speed
preset first, and verify:

```powershell
curl http://127.0.0.1:8080/v1/models
```

For the 1M preset, warm up in the same boot: **40k → 256k → 1M**. A cold 1M request is how
`experts_native: an illegal memory access was encountered` appears.

## Step 6 — validate the measurement

```powershell
python tools\prefill_real_bench.py --label recovery-40k --size 40960 --runs 3 ^
  --max-tokens 64 --temperature 0 --out recovery-40k.jsonl
```

Expected on the original machine, 512k routed preset:

- prefill median ~2,100 t/s @40k, peak ~2,105;
- decode median ~53 t/s across 38–43 generated tokens;
- KV `int8`, no `--max-tokens` in the preset, temperature 1 in the preset (the benchmark
  client alone uses temperature 0).

If the prefill is ~1,720 t/s, the ring env vars were not applied. If it is ~14% low, the boot
was not unlocked. If it collapses entirely, check RAM size and XMP.

## Step 7 — agent/API checklist

An automated agent can treat the above as a state machine:

| Check | Pass condition |
|---|---|
| Repo cloned | `git rev-parse --is-inside-work-tree` → true |
| Payload intact | `.\verify.ps1` → 0 |
| Pendrive unlocked | `loader.log` contains `plm_open=true` |
| Python/CUDA | `python -c "import nvidia"` → 0 |
| Shards present | both IQ3_S `.gguf` files readable |
| Presets rendered | `args == args_written` in both JSONs |
| Engine up | `/v1/models` returns 200 |
| Warm-up done | 40k then 256k succeeded in same boot before 1M |
| 40k sanity | prefill median within ~10% of 2,100 t/s |

Stop and report at the first failed check. Do not guess around a failed hash or a missing
shard.
