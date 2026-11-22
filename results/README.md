# Results — what is shipped vs. what is history

The landing page and README quote **only** the two presets in `presets/`. These are the
files that back those numbers:

| File | Contents |
|---|---|
| `shipped-512k-routed-40k.jsonl` | The three fresh 40k requests behind 2,100.5 t/s median and 53.3 t/s decode median. |
| `shipped-512k-routed-ramp.jsonl` | The same 40k requests plus 200k / 350k / 500k, extracted from the engine log of that exact preset. |
| `calib-1m-h4-final-20261122.jsonl` | The 40k → 256k → 1M warm ramp on `strata-1m-h4`, from the engine log. |

The remaining `calib-*.jsonl` files are **historical tuning evidence**. They contain
discarded variants (ring512 plain, kv-grow, headroom 2, older engines and drafts, short
and long generations) and are kept so the exploration is auditable. Do not quote numbers
from them as if they belonged to either shipped preset.

In particular:

- **73.4 t/s** decode in `calib-df2-20261120.jsonl` is a pre-routed 40k OC tuning run.
- **106.3 t/s** decode in `calib-results.jsonl` is from 08/11, engine **0.1.58**, MTP `rt`
  draft and 512 generated tokens. Neither engine, draft nor preset is shipped here.

Decode figures in the showcase are short-answer samples (38–43 tokens on the 40k runs,
64 tokens on the 1M ramp, 256 tokens on the 512k long ramp). They are reported for context,
not as a long-output decode benchmark.
