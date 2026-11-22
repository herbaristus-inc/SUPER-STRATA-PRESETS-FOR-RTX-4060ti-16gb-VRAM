# Related public numbers (what I compared against)

I checked these before publishing. I am **not** claiming a world record — I am publishing
my measurements and the sources so others can judge. All figures are `t/s` of prompt
processing (prefill), not decode and not time-to-first-token.

| Source | Hardware / model | Prefill |
|---|---|---:|
| [Niko1221/Strata#3558](https://github.com/Niko1221/Strata/issues/3558) | RTX 4060 Ti 16 GB, i5-13400, 64 GB DDR5-6000, Strata 0.1.46, IQ3_XXS, up to ~140k | 1,062 median zero-reuse / 1,204.5 mostly-fresh (range 769–1,266) |
| [Niko1221/Strata#3976](https://github.com/Niko1221/Strata/issues/3976) | 2x RTX 4060 Ti 16 GB, 128 GB, Linux, engine 0.1.53, UD-IQ4_XS @79k | 2,410–2,441; IQ3_S up to 2,653 |
| [Official speed report 0.1.22](https://github.com/Niko1221/Strata/blob/main/docs/bench-results/2026-09-29-speed-0122/README.md) | RTX 5070 12 GB + 64 GB, IQ3_S @32k | 1,499 (Q2_0 1,844; Coder 1,871) |
| [`docs/MODELS.md`](https://github.com/Niko1221/Strata/blob/main/docs/MODELS.md) (0.1.26) | RTX 5070 12 GB, IQ3_S @32k | 1,620 (Q2_0 2,650) |
| [Community benchmarks](https://github.com/Niko1221/Strata/blob/main/docs/COMMUNITY_BENCHMARKS.md) | 2x TITAN RTX @128k / Strix Halo 70W @32k / RX 9070 @130k | 1,626.9 / 1,067 / 833 |
| [llamaperf GPU page](https://llamaperf.com/gpu/rtx-4060-ti-16gb?sort=fastest-pp) | RTX 4060 Ti 16 GB, highest community run (27B dense, llamADALL fork) | 870 |
| [Hardware Corner](https://www.hardware-corner.net/gpu-llm-benchmarks/rtx-4060-ti-16gb/) | RTX 4060 Ti, 14B Q4 @16k | 918 |
| [araoai](https://araoai.com/en/hardware/NVIDIA%20RTX%204060%20Ti%2016GB) | vLLM Q2_K on 0.5–4B models | 1,317 |

The `1,100–1,300 t/s` range people quote for 4060 Ti 16 GB + 64 GB is real — issue #3558
is almost the same machine. The difference here is the ring512 / routed-stream tuning and,
for the 1M preset, a deliberately different capacity/speed trade-off.

**Do not compare GPU model alone.** Every number above that involves Qwen3.8-Flash-Next
IQ3_S assumes enough host RAM to pin the expert arena. On 32 GB the same card drops to the
SSD tier and none of these prefill figures are reachable. The relevant system is
"RTX 4060 Ti 16 GB + 64 GB DDR5", not just the GPU.

## Why the numbers are not directly comparable

- Prompt-processing `t/s` is not TTFT. A cached prefix can make TTFT tiny while doing no work.
- Prompt length changes the number a lot. A 4k and a 32k result on the same card are not the
  same measurement.
- Model size and quant matter: a 27B dense model at Q4 is not a 125B MoE at IQ3_S.
- My prompts are nonce-unique realistic documents, not the repo's standard word-list suite.
  For a like-for-like submission to the Strata repo, run `strata bench run` and attach its
  `results.json`.

If you find a single-card 4060 Ti result above 2,100 t/s on this model, open an issue here —
I would rather have the correct number on the table.
