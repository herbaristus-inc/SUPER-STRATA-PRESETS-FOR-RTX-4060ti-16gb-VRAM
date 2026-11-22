# Why this model: Qwen3.8-Flash-Next GSQ-RCO IQ3_S

The presets are tuned for **Qwen3.8-Flash-Next GSQ-RCO IQ3_S**, published by ISTA-DASLab:

<https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF>

This is not a generic IQ3_S quant. It is the ISTA-DASLab **GSQ-RCO** family — the quantisation
closest to the BF16 original at a size that fits a 16 GB card plus 64 GB of host RAM.

## What GSQ-RCO does

From the model card:

> "GSQ provides accurate low-bit scalar quantization of each tensor at a given quantization
> type; RCO assigns the per-tensor quantization types under a size budget. Together they
> yield a non-uniform GGUF at the requested size."

- **GSQ** = Gumbel-Softmax Quantization. It learns grid assignments and group scales jointly,
  closing most of the gap between scalar and vector quantisation at 2–3 bits while staying in
  standard scalar GGUF formats.
- **RCO** = Riemannian Constrained Optimization. It assigns one quantisation type per tensor
  under a total size budget, using the task loss as the search signal.
- The search covers **352 tensors**: 304 dense tensors plus 48 fused routed-expert matrices.
  Since 95% of searchable weights are experts, this matters enormously for a 125B MoE.
- The output is a **standard GGUF** that runs unmodified in llama.cpp, Ollama, LM Studio and
  Strata. Two shards: shard 1 holds transformer weights and must be resident; shard 2 is the
  51.2B n-gram embedding table at IQ4_NL and is read one row per token, so it can stay on SSD.

## Why IQ3_S specifically

The model card publishes this comparison against the BF16 base (354 GB):

| Variant | bpw | Total size | AIME25 | GPQA-D | LCB v6 | Task avg |
|---|---:|---:|---:|---:|---:|---:|
| BF16 | 16.00 | 354 GB | 100.00 | 91.92 | 87.43 | 93.12 |
| IQ3_XXS | 3.00 | 75.8 GB | 100.00 | 91.41 | 86.29 | 92.57 |
| **IQ3_S** | **3.50** | **83.6 GB** | **100.00** | **92.93** | **86.86** | **93.26** |

The card calls IQ3_S "Recommended; matches or exceeds the base model on every task" and
describes it as the strongest operating point — parity on AIME25, ahead on GPQA-Diamond,
within 0.57 points on LiveCodeBench v6, at under a quarter of the BF16 size.

It also warns, honestly, that numbers slightly above 100% are **benchmark variance**, not
proof that a quant is better than its source:

> "recoveries slightly above 100% reflect benchmark variance, not a model that is better than
> the one it was quantized from."

So the accurate claim is: **IQ3_S is at parity with BF16 on these tasks**, and it is the
largest/most faithful quant in the family that still fits this machine. It is not literally
lossless, and the card reports no perplexity table.

## Why it works with these presets

- 125B total parameters, ~6B active, 512 experts. Strata keeps the expert arena in pinned
  host RAM and streams hot experts into VRAM — exactly what 64 GB DDR5 + one 16 GB card is for.
- The n-gram shard stays memory-mapped on SSD; only shard 1 needs to be resident.
- KV cache is `int8` — the quant of the **cache**, not of the experts. The `q4_0` selector in
  the draft pack is only for the DFlash2 draft head.
- The DFlash2 draft (`qwen3.8-flash-next-dflash2.strata1.q4_0-selq4.pack`) is matched to this
  model; do not swap it for the older MTP `rt` draft from pre-0.1.62 configs.

## What not to substitute

- `Q2_0` is faster (the card reports 367.49 prompt t/s in its own tests) but is a different
  accuracy point. It is not what these numbers measure.
- IQ3_XXS is smaller but gives back task-average points.
- A uniform IQ3_S quant of another conversion is **not** the same thing as GSQ-RCO IQ3_S.
  The per-tensor assignment is the point.

Download the two shards and the BF16 `mmproj` from the linked repo. This repository ships no
weights.
