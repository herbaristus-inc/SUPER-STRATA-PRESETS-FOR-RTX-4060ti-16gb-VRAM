# Strata prefill presets for a single RTX 4060 Ti 16 GB

Two tuned `Strata` configs for **Qwen3.8-Flash-Next IQ3_S (125B MoE, 6B active)** on one
RTX 4060 Ti 16 GB + 64 GB system RAM. Engine and Control **0.1.62**, DFlash2 draft pack,
`kv int8`, vision on CPU, abliteração/speed-projection on, temperature 1, no `max_tokens`
in the preset.

This is a **single-GPU, consumer-hardware** result. It is not a server recipe and it does
not use `q4_0` KV, extra cards, or `--kv-grow`.

> **The GPU alone is not enough.** These numbers need **64 GB of system RAM (DDR5)**.
> Strata keeps the whole 125B expert set in pinned host memory and streams only the hot
> experts into VRAM. With 32 GB the IQ3_S weights do not fit and the engine falls back to
> mmap/SSD tier — you will not see these speeds no matter which 16 GB card you put in the
> slot. RAM capacity, dual-channel bandwidth and the pinned/page-locked arena are half of
> this result. Treat "4060 Ti 16 GB + 64 GB DDR5" as one system.

| Preset | Window | Best measured prefill | Long-prompt measured prefill |
|---|---:|---:|---:|
| `strata-512k-routed` | 524,288 | **2,104.8 t/s** @ ~41k (median **2,100.5**) | 1,647.7 t/s @ 500k |
| `strata-1m-h4` | 1,048,576 | **1,767.8 t/s** @ ~263k | **1,253.7 t/s** @ 1,000,807 tokens |

Both presets were measured with fresh nonce-unique realistic prompts, `temperature 0` on
the benchmark client only, and the engine's own `prompt_tps` timing. Raw JSONL is in
[`results/`](results/).

> **Honest scope note:** this is the fastest single-4060-Ti prefill I could find published
> for this model, but **I am not claiming a world record**. Two RTX 4060 Ti cards with 128 GB
> RAM have published ~2,410–2,650 t/s at 79k (`Niko1221/Strata#3976`), and there is no official
> leaderboard for this metric. See [RELATED.md](RELATED.md) for every source I checked.

---

## Hardware

| Part | Value |
|---|---|
| GPU | RTX 4060 Ti 16 GB (VRAM OC via `Strata VRAM OC 10827.bat`), one card |
| System RAM | **64 GB DDR5, dual channel — required, not optional** |
| Why RAM matters | Full expert arena lives in pinned RAM: ~37 GiB page-locked at 1M on top of 12.38 GiB of `int8` K/V. At 32 GB the weights spill to SSD and the numbers collapse. |
| Vision | `--vision` with `vision.gpu: false` (CPU / SSD tower) |
| Serving stack | `engine-feed/control/0.1.62/serve/server.py` → Strata engine 0.1.62 |
| Model | Qwen3.8-Flash-Next GSQ-RCO IQ3_S, pack + expert-profile DFlash2 tuned |
| Draft | `qwen3.8-flash-next-dflash2.strata1.q4_0-selq4.pack` (Q4_0 selector) |
| KV | `int8`, `--kv-resident 32768` |
| OS | Windows 11, dedicated GPU reserved for Strata |
| GPU preference | `HKCU\Software\Microsoft\DirectX\UserGpuPreferences` routes other apps to iGPU |

---

## The five levers that actually moved the needle

These are the settings that mattered, in order of impact. All are plain flag/env changes —
no source patching.

1. **`STRATA_PREFILL_RING=512`** — the big one. Plain `kv-resident` was ~1,720 t/s; ring512
   pushed it to ~2,098 t/s at 40k. The engine's default ring 96 was the ceiling.
2. **`STRATA_PREFILL_ROUTED_STREAM=1`** — small but consistent extra, chosen after a duel
   against plain ring512 at 200k / 350k / 500k.
3. **`--kv int8 --kv-resident 32768`** — `kv-grow` hits ~2,148 t/s at 40k but dies near 160k
   with `the K/V could not grow ... no VRAM is left`. Resident KV is what makes 500k/1M pass.
4. **`--rope-scale 4` + `STRATA_PREFILL_TAIL_LOAN=0`** — only for the 1M preset. Without the
   tail-loan variable the first request dies with
   `experts_native: an illegal memory access was encountered`. See [PITFALLS.md](PITFALLS.md).
5. **`STRATA_RESIDENT_HEADROOM_GIB=4`** — only for the 1M preset. Cuts the expert file tier
   from ~13 GiB to ~8.6 GiB for +4–10% prefill. `=2` was tested and rejected: page-locking
   is refused and the gain vanishes at 1M. This lever exists **only because there are 64 GB
   of RAM to allocate from** — on a 32 GB machine it has nothing to trade with.

---

## Why 1M is slower than 512k

At 1M the `int8` K/V alone takes **12.38 GiB of pinned RAM** (6.19 GiB at 512k). The expert
arena no longer fits and falls back to `FileExpertSource` + ~37 GiB page-locked complement,
with a file tier left over. The prefill planner picks 4 chunks per 32k instead of 3. The
full 1M ramp read roughly 3.95 TB from the GGUF. It is a capacity cost, not instability —
the endpoint stayed `loaded` with `n_ctx 1048576` after every test.

---

## Reproduce

```bash
# 1. render a preset for your paths
python tools/render_preset.py presets/strata-512k-routed.json.template \
  --strata-root /path/to/Strata \
  --strata-data /path/to/Strata-data \
  --python /path/to/python.exe \
  --out strata-512k-routed.json

# 2. start Strata Control 0.1.62 with that config, wait for `window warm-up` in the log

# 3. run the realistic benchmark (fresh nonce, temperature 0, 40k example)
python tools/prefill_real_bench.py --label my-40k --size 40960 --runs 3 \
  --max-tokens 64 --temperature 0 --out my-run.jsonl
```

**Benchmark protocol:** warm the engine with one short request first, then use nonce-unique
heterogeneous prompts (runbook, C++ source, incident timeline, JSON snapshot, git diff,
stack trace, benchmark notes, design doc, and one real debugging task). Never reuse a prompt.
Report medians, not peaks, and quote the actual token count from the JSONL.

Long ramps must be launched **detached** from any agent/tool shell — a child process gets
killed at ~2 minutes in the middle of a request. Use a standalone `.bat`/`.sh`.

---

## Files

- `presets/strata-512k-routed.json.template` — 512k speed preset
- `presets/strata-1m-h4.json.template` — 1M capacity preset
- `tools/render_preset.py` — fill in your paths, validate `args == args_written`
- `tools/prefill_real_bench.py` — realistic corpus benchmark
- `results/*.jsonl` — raw measurements, one JSON object per request
- [PITFALLS.md](PITFALLS.md) — discarded levers and the crash that cost a day
- [RELATED.md](RELATED.md) — public numbers I compared against, with links

Licensed MIT. The model, draft pack and experimental-speed-projection vector keep their
own licenses — this repo ships configs and measurements only, no model weights.
