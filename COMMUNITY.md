# Bring your own GPU

These two presets were tuned on **one RTX 4060 Ti 16 GB + 64 GB DDR5**, but the levers are
not card-specific: the pinned expert arena, `kv-resident`, the 512-token prefill ring and the
routed stream are Strata settings, not 4060 Ti magic.

If you run a **RTX 5080 / 5070 Ti / 4070 Ti Super / 4080 / 4090**, or any other 16 GB+ card,
please try them and post your result. We want to know how much transferable gain is really
there — positive or negative.

## What to try

1. Start with `presets/strata-512k-routed.json.template` — the speed preset.
2. If your VRAM and RAM allow it, try `presets/strata-1m-h4.json.template` — the capacity preset.
3. Warm up with a short request; for the 1M preset use **40k → 256k → 1M in the same boot**.
4. Use fresh, nonce-unique prompts. Do not measure a cached prefix and call it prefill.
5. Report the engine's `prompt_tokens` and `prompt_tps` from a raw log, not a panel average.

## Result template

Copy this into an issue or discussion:

```markdown
### Preset
- [ ] strata-512k-routed
- [ ] strata-1m-h4

### Hardware
- GPU / VRAM:
- VRAM clock:
- System RAM (size, DDR generation, speed):
- Display adapter (iGPU or dedicated):
- Unlocked boot: yes / no / unknown
- Engine + Control version:

### Measurement
- Prompt length (actual `prompt_tokens`):
- Reused tokens:
- Prefill t/s (median of at least 3 fresh requests):
- Decode t/s and generated tokens:
- Any errors / breaks:

### Raw evidence
- JSONL or Strata log attached: yes / no
```

## Honest expectations

- If you have **less than 64 GB system RAM**, do not expect these numbers: the expert arena
  spills to the SSD tier. This is the single biggest confounder.
- Faster cards with more VRAM may need different `--kv-resident` and headroom values. Start
  from the shipped config, then change one variable at a time and say what you changed.
- `STRATA_PREFILL_TAIL_LOAN=0` is mandatory for the 1M preset. Removing it caused
  `experts_native: an illegal memory access was encountered` on this machine.
- No record claim. The point is to find out what transfers.

Results that reproduce, and results that fail, are equally useful. Please include the raw
log either way.
