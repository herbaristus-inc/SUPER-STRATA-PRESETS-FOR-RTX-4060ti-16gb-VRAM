# Notes for the Strata maintainers

Prepared from measurements on **engine 0.1.62 / Control 0.1.62**, Qwen3.8-Flash-Next
IQ3_S (ISTA-DASLab / GSQ-RCO), one RTX 4060 Ti 16 GB and 64 GB DDR5-6000. Everything below
is a reproducible observation, not a request for a benchmark leaderboard entry.

## 1. `STRATA_PREFILL_RING=512` is the big lever

Plain `--kv int8 --kv-resident 32768` sat at **~1,720 t/s** prefill on a fresh 40k prompt.
Setting the prefill ring to 512 raised it to **~2,098 t/s** — the engine's own panel showed
2,077 t/s average and 2,105 peak over three fresh 40,989-token requests.

`STRATA_PREFILL_ROUTED_STREAM=1` added a small but repeatable win at 200k / 350k / 500k.
Together these are the "512k routed" preset: 2,100.5 t/s median @40k, 1,647.7 t/s @500k,
no breaks through the 524,288-token window.

## 2. The 1M window needs a different shape

`--max-context 1048576 --rope-scaling yarn --rope-scale 4` reaches 1,000,807 tokens at
1,253.7 t/s with the ring512 preset, warmed 40k → 256k → 1M in one boot. Zero breaks.

Two settings are non-optional:

- **`STRATA_PREFILL_TAIL_LOAN=0`** — without it, on this machine the first 1M request died
  with `experts_native: an illegal memory access was encountered`. The fault correlates with
  the 1M chunk/tail layout (`tail 0`, stream floor 3071, chunk 10496).
- **`STRATA_RESIDENT_HEADROOM_GIB=4`** — drops the file tier from ~13 GiB to ~8.4–9.2 GiB
  for +4–10% prefill. `=2` was tested and rejected: page-locking was refused, the engine
  fell back to pageable memory plus `VirtualLock`, and the 1M gain was ~0.6%.

## 3. `kv-grow` cannot hold this model at long context

`--kv-grow` reached ~2,148 t/s at 36–40k but died near 160k with
`the K/V could not grow ... no VRAM is left`. `STRATA_KV_GROW_FLOOR=512` was inert.
`kv-resident` is the only stable path we found for 500k/1M on 16 GB VRAM.

## 4. Levers that did nothing

`STRATA_PREFILL_CPU_SHARE=auto`, `lend100`, `--prefill-head-alias` (unavailable without
`--mtp`), `STRATA_PF_WMMA=1`, and power-limit 198 W. Reported so others do not repeat them.

## 5. What is actually required to reproduce

The model is a 125B MoE served from pinned host RAM with VRAM as a hot cache. **64 GB DDR5
is required**; 1M `int8` K/V alone is 12.38 GiB pinned, on top of a ~37 GiB expert arena.
On 32 GB the weights spill to SSD and none of the above speeds are reachable. The display
adapter was the iGPU, with browsers and Electron apps pinned to it via
`HKCU\Software\Microsoft\DirectX\UserGpuPreferences` (`GpuPreference=1`).

## 6. Method

Benchmark: `tools/prefill_real_bench.py` — heterogeneous engineering corpus, fresh `nonce`
per request, engine-reported `prompt_tps`, medians of three or more runs. Long ramps were
run detached from the agent shell; a child process gets killed at ~2 minutes. Decode
samples in this repo are short answers (38–43 generated tokens) and are **not** a
long-output decode benchmark.

## Suggested upstream changes

- Document the ring / routed-stream env vars and their interaction with `--kv-resident`.
- Consider warning when `--kv-grow` is combined with a large context on 16 GB cards.
- Investigate the 1M tail-loan crash so `STRATA_PREFILL_TAIL_LOAN=0` is not needed forever.

Raw JSONL, sanitized presets, renderer, launcher templates and the realistic benchmark are
in this repository. No model weights or third-party unlocker image are included.
