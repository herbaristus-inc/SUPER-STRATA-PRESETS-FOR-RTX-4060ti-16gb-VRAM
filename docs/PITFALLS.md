# Pitfalls — things that failed so you don't repeat them

All of these were measured on the same RTX 4060 Ti 16 GB + 64 GB box with engine/Control
0.1.62. "Discarded" means it either lost the A/B or broke something.

## Fatal

### 1M without `STRATA_PREFILL_TAIL_LOAN=0`
First request dies with:

```
prefill fused experts (native): experts_native: an illegal memory access was encountered
```

The 1M config picks a 10,496-token chunk; the engine logs
`lent prompt buffers are sized ... tail 0 tokens, not the stream floor's 3071`. Some layer
then runs MMQ inside a fused-layout buffer that is too short. Forcing the floor-sized
buffers fixes it. The 512k champion also logs `tail 0` without crashing (chunk 15,104/16,128),
so the warning alone is harmless — it is the combination with the 1M chunk that kills it.

### `--kv-grow` at long context
~2,148 t/s at 36–40k, then at 160k+: `the K/V could not grow ... no VRAM is left`. The expert
cache floor (~4,049 slots) plus K/V expansion exhausts the card. `STRATA_KV_GROW_FLOOR=512`
is inert — the floor stayed at 4,049 slots and the model was ejected.

### `--prefill-head-alias`
Refused at startup: `--prefill-head-alias is unavailable: it needs --mtp`. DFlash2 plus
`--mtp-draft-vocab` does not count as `--mtp`.

## Measured, no gain

| Lever | Result |
|---|---|
| `STRATA_PREFILL_CPU_SHARE=auto` | 1,720 t/s, no change; warns only ~2 GiB RAM free |
| `STRATA_PREFILL_LEND_PCT=100` | chunk 16,128 → 19,200, speed unchanged |
| `STRATA_PREFILL_LAYER_MAJOR=1` | 2,062 t/s, slower than ring512 |
| `STRATA_PREFILL_AUTO_MAX=24576` | 2,096.9 t/s, chunk unchanged |
| `--kv-resident 49152` + ring512 | 2,089.6 t/s, slower than 32,768 |
| `STRATA_RESIDENT_HEADROOM_GIB=2` (1M) | 1,261.5 t/s @1M vs 1,253.7 @h4 — +0.6%, but page-locking refused and Windows is left with ~1.9 GiB free |

## Operational

- Kill the old `serve/server.py` terminal before starting a new one. Two Control processes
  on port 8080 is a silent trap.
- Never send 1M into a cold engine. Warm with 40k then 256k in the same boot; the ramp curve
  changes otherwise.
- `window warm-up` must finish before the first timed request.
- A process launched as a child of an agent shell dies when the shell closes — detach it.
