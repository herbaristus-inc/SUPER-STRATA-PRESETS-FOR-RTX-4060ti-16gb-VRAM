#!/usr/bin/env python3
"""Heavy realistic prefill bench: heterogeneous engineering corpus, unique nonce.

Unlike prefill_bench.py (synthetic word lists), this builds a realistic
agent boot payload: source code, configs, logs, diffs, stack traces, docs
and a genuine debugging task at the end. Token count is measured with the
pack's own tokenizer and topped up to an exact floor.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def find_tokenizer_dir() -> Path | None:
    cfgs = [p for p in ROOT.glob("strata-*.json") if not p.name.endswith(".shared-settings.json")]
    for p in sorted(cfgs, key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            tok = json.loads(p.read_text(encoding="utf-8")).get("tokenizer")
        except (OSError, ValueError):
            continue
        if tok and (Path(tok) / "vocab.json").exists():
            return Path(tok)
    return None


def load_tokenizer(tok_dir: Path):
    import strata_tokenizer as ST
    vocab = json.loads((tok_dir / "vocab.json").read_text(encoding="utf-8"))
    tokens = [None] * len(vocab)
    for t, i in vocab.items():
        tokens[i] = t
    merges = (tok_dir / "merges.txt").read_text(encoding="utf-8").split("\n")
    types = json.loads((tok_dir / "token_type.json").read_text())
    try:
        tcfg = json.loads((tok_dir / "tokenizer.json").read_text(encoding="utf-8"))
    except OSError:
        tcfg = {}
    return ST.Tokenizer(tokens, merges, types, tcfg.get("pre") or "qwen35", tcfg.get("special_ids") or None)


def corpus_block(i: int, nonce: str, seed: int) -> str:
    """One realistic, non-repeating engineering document (~1.5-3k tokens)."""
    k = i % 8
    tag = f"{nonce}-{i:05d}-{seed}"
    if k == 0:
        return "\n".join([
            f"# SERVICE RUNBOOK — strata-inference ({tag})",
            "",
            "## Symptoms",
            f"After {100 + i} minutes of sustained traffic, prefill throughput drops from ~2100 tok/s to "
            f"~{1700 + i % 90} tok/s. The engine logs `only 0 MiB of VRAM free` and then "
            "`the K/V could not grow to 180224 cells (no error)`.",
            "",
            "## Environment",
            f"- GPU: RTX 4060 Ti 16 GB, VRAM locked at 10827 MHz, SM {2850 + i % 40} MHz under load",
            f"- RAM: DDR5-6000 64 GiB, available {1 + i % 7}.{i % 10} GiB at request start",
            "- Engine 0.1.62, Control 0.1.62, CUDA 13, driver PLM unlocked",
            "- KV int8, YaRN scale 2, 524288 context, DFlash2 Q4_0 tuned pack",
            "",
            "## Investigation notes",
            f"1. Expert cache auto-sized to {4000 + i % 80} slots ({7.5 + i % 9 / 10:.1f} GiB).",
            "2. K/V growth takes VRAM from the cache floor; cache floor is 3836 slots.",
            "3. Streaming block hit rate stays above 90% even at long context.",
            f"4. Observation id {tag}: Windows WDDM starts paging when free VRAM reaches zero.",
            "",
            "## Open question",
            "Why does the expert cache refuse to release more slots when the driver still reports "
            "hundreds of MiB theoretically free?",
        ])
    if k == 1:
        lines = [
            f"// src/prefill/kv_resident.cpp — revision {tag}",
            "#include <cuda_runtime.h>",
            "#include <vector>",
            "",
            "namespace strata {",
            "",
            "struct KVCell {",
            "    int8_t k[512];",
            "    int8_t v[512];",
            "    uint16_t scale;",
            "};",
            "",
            f"class KVResident final {{",
            f" public:",
            f"  explicit KVResident(size_t cells) : cells_(cells), pinned_(nullptr) {{",
            f"    // {tag}: reserve pinned host memory for the full K/V set",
            f"    cudaHostAlloc(&pinned_, cells * sizeof(KVCell), cudaHostAllocPortable);",
            "  }",
            "  ~KVResident() { if (pinned_) cudaFreeHost(pinned_); }",
            "",
            "  bool ensure(size_t needed) {",
            "    if (needed <= vram_cells_) return true;",
            "    size_t want = needed - vram_cells_;",
            "    if (!cache_->release(want)) {",
            "      log_warn(\"the K/V could not grow to %zu cells\", needed);",
            "      return false;",
            "    }",
            "    vram_cells_ = needed;",
            "    return true;",
            "  }",
            "",
            " private:",
            "  size_t cells_ = 0;",
            "  size_t vram_cells_ = 0;",
            "  void* pinned_ = nullptr;",
            "  ExpertCache* cache_ = nullptr;",
            "};",
            "",
            "}  // namespace strata",
        ]
        for j in range(6):
            lines += [
                f"// variant {j} of {tag}: alternative cache-release policy",
                f"static bool try_release_{j}(ExpertCache& c, size_t want) {{",
                f"  const size_t floor = {3000 + j * 150};",
                "  if (c.slots() - want < floor) return false;",
                "  return c.release(want);",
                "}",
            ]
        return "\n".join(lines)
    if k == 2:
        rows = [
            f"# incident timeline {tag}",
            "",
            "| ts | event | vram_free | kv_cells | cache_slots | tps |",
            "|---|---|---:|---:|---:|---:|",
        ]
        for j in range(40):
            rows.append(
                f"| 18:{j % 60:02d}:{(j * 7) % 60:02d} | "
                f"{['prompt accepted','chunk read','kv grown','expert swapped','decode window','warning'][j % 6]} | "
                f"{max(0, 740 - j * 25)} | {16384 + j * 4096} | {4053 - j * 47} | {2100 - j * 9} |"
            )
        rows += ["", f"Trace id {tag}: the last three rows precede the engine restart.", ""]
        return "\n".join(rows)
    if k == 3:
        cfg = {
            "incident": tag,
            "engine": "0.1.62-windows-x86_64-cuda-cuda13",
            "model": "qwen3.8-flash-next-iq3_s",
            "args": ["--kv", "int8", "--kv-grow", "--max-context", "524288",
                     "--prefill", "auto:32768", "--expert-cache", "auto", "--vision"],
            "env": {"STRATA_PF_FUSED": "1", "STRATA_PIN_RESERVE_MIB": "160"},
            "measurements": [
                {"prompt": 36864, "tps": 2146.9 + i % 5, "peak": 2148.8, "run": j}
                for j in range(12)
            ],
            "notes": "Expert cache floor 3836 slots; K/V growth stalls at 172032 cells.",
        }
        return f"// config snapshot {tag}\n" + json.dumps(cfg, indent=2, ensure_ascii=False)
    if k == 4:
        lines = [
            f"diff --git a/src/prefill/prompt.cpp b/src/prefill/prompt.cpp",
            f"index {tag[:8]}..{tag[9:17]} 100644",
            "--- a/src/prefill/prompt.cpp",
            "+++ b/src/prefill/prompt.cpp",
            "@@ -120,6 +120,14 @@ void PromptPath::layout() {",
            "   auto slots = cache_->borrow(needed);",
            "   if (!slots) {",
            "+    // Retry with a smaller ring before giving up on the chunk.",
            "+    for (int ring = 512; ring >= 96; ring /= 2) {",
            "+      auto retry = cache_->borrow_with_ring(needed, ring);",
            "+      if (retry) {",
            "+        log_info(\"prompt ring %d accepted\", ring);",
            "+        slots = retry;",
            "+        break;",
            "+      }",
            "+    }",
            "   }",
        ]
        for j in range(18):
            lines += [
                f"@@ -{200 + j * 17},{j % 5 + 1} +{208 + j * 17},{j % 5 + 1} @@ int helper_{j}(int x) {{",
                f"-  return x * {j};",
                f"+  return x * {j} + {i % 7};  // {tag}",
            ]
        return "\n".join(lines)
    if k == 5:
        lines = [
            f"FATAL: unhandled exception in worker thread — incident {tag}",
            "Stack trace:",
        ]
        for j in range(30):
            lines.append(
                f"  #{j:02d} 0x{(0x7ff00000 + i * 4096 + j * 37):012x} "
                f"strata::{['prefill','expert_cache','kv_stream','verify','router','pool'][j % 6]}::"
                f"function_{j}(strata::Context* ctx, size_t arg={j * 13 + i % 11})"
            )
        lines += [
            "",
            f"Last log lines before the fault ({tag}):",
            "  strata serve: WARNING: only 0 MiB of VRAM free at the start of this request",
            "  strata: the elastic K/V could not map 2 chunks (the driver has no VRAM left)",
            "  strata: K/V grown to 172032 cells (2.06 GiB); the expert cache gave 0 slots for it",
            "  strata: the K/V could not grow to 180224 cells (no error)",
        ]
        return "\n".join(lines)
    if k == 6:
        lines = [f"# Benchmark notes — {tag}", ""]
        for j in range(45):
            lines.append(
                f"- Run {j:03d} ({tag}): chunk {16000 + j * 64}, ring {96 if j % 3 else 512}, "
                f"borrowed {3300 + j * 7} slots, block hits {90 + j % 8}.{j % 10}%, "
                f"prefill {1650 + j * 3}.{j % 10} tok/s, decode {45 + j % 20}.{j % 10} tok/s."
            )
        lines += ["", "Conclusion: ring size, not chunk size, predicts prefill speed on the resident path."]
        return "\n".join(lines)
    lines = [
        f"# Design doc: expert cache vs K/V residency ({tag})",
        "",
        "## Problem",
        "On a 16 GiB card the model weights, DFlash2 drafter, expert cache and full int8 K/V "
        "cannot coexist. Two placement policies exist.",
        "",
        "## Option A: elastic kv-grow",
        "K/V starts small and grows into VRAM freed by the expert cache. Fast prefill "
        "(~2100 tok/s at 40k) but stalls near 172k cells because the cache has a floor.",
        "",
        "## Option B: kv-resident",
        f"The full K/V ({tag}) lives in 6.19 GiB of pinned host RAM; 32768 cells stay in VRAM. "
        "520k prompts complete without errors, but prefill was ~1720 tok/s until the prompt "
        "ring was raised from 96 to 512, reaching ~2100 tok/s.",
        "",
        "## Measurements",
    ]
    for j in range(25):
        lines.append(
            f"  config ring={96 if j % 2 else 512} lend={85 if j % 3 else 100}: "
            f"run {j} -> {1700 + j * 16} tok/s"
        )
    lines += [
        "",
        "## Decision",
        "Prefer kv-resident with ring 512: it keeps the 524288 window honest at every prompt length.",
    ]
    return "\n".join(lines)


TASK = (
    "\n\n---\n\n"
    "TAREFA REAL: Você é o engenheiro de plantão responsável por este serviço. "
    "Leia todo o material acima (código, configs, timelines, diffs, stack traces e notas). "
    "Identifique a causa raiz da queda de prefill e do erro de crescimento do K/V em 160k contexto, "
    "aponte pelo menos três evidências concretas com os números que aparecem no material, "
    "e proponha uma correção com as flags/configurações exatas. "
    "Responda em português, de forma objetiva."
)


def build_prompt(target: int, nonce: str, tok) -> str:
    blocks = []
    n = 0
    i = 0
    while n < target:
        b = corpus_block(i, nonce, i * 31 + 7)
        blocks.append(b)
        n += len(tok.encode(("\n\n" if i else "") + b))
        i += 1
    return "\n\n".join(blocks) + TASK


def one_request(url: str, prompt: str, max_tokens: int, temperature: float):
    body = {
        "model": "local",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": {"enable_thinking": False},
    }
    req = urllib.request.Request(
        url.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.monotonic()
    usage = timings = None
    snippet = ""
    with urllib.request.urlopen(req, timeout=3600) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                j = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if j.get("usage"):
                usage = j["usage"]
            if j.get("timings"):
                timings = j["timings"]
            for ch in j.get("choices", []):
                d = ch.get("delta") or {}
                piece = d.get("content") or d.get("reasoning_content")
                if piece and len(snippet) < 2000:
                    snippet += piece
    u, t = usage or {}, timings or {}
    cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    pt = u.get("prompt_tokens") or 0
    pp = t.get("prompt_per_second")
    if not pp and t.get("prompt_ms") and pt:
        pp = (pt - cached) / (t["prompt_ms"] / 1000)
    return {
        "prompt_tokens": pt, "reused": cached, "prompt_tps": round(pp, 1) if pp else None,
        "prompt_ms": t.get("prompt_ms"), "decode_tps": t.get("predicted_per_second"),
        "total_s": round(time.monotonic() - t0, 2), "answer_head": snippet[:300],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--size", type=int, default=200000)
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--out", default="calib-real-20261120.jsonl")
    a = ap.parse_args()

    tok_dir = find_tokenizer_dir()
    if tok_dir is None:
        raise SystemExit("no tokenizer found")
    tok = load_tokenizer(tok_dir)
    records = []
    for run in range(a.runs):
        nonce = uuid.uuid4().hex[:12]
        print(f"building realistic corpus for {a.size} tokens (nonce {nonce})...", flush=True)
        prompt = build_prompt(a.size, nonce, tok)
        actual = len(tok.encode(prompt))
        print(f"prompt built: {actual} tokens, {len(prompt)} chars — sending", flush=True)
        try:
            r = one_request(a.url, prompt, a.max_tokens, a.temperature)
        except Exception as e:
            print(f"run{run+1}: ERROR {e}", flush=True)
            records.append({"label": a.label, "run": run + 1, "error": str(e)})
            continue
        r.update({"label": a.label, "target": a.size, "run": run + 1})
        records.append(r)
        print(f"  run{run+1}: prompt {r['prompt_tokens']} tok (reused {r['reused']}) -> "
              f"{r['prompt_tps']} tok/s | total {r['total_s']} s", flush=True)
        print(f"  answer head: {r['answer_head'][:200]!r}", flush=True)
    with open(a.out, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"saved -> {a.out}", flush=True)


if __name__ == "__main__":
    main()
