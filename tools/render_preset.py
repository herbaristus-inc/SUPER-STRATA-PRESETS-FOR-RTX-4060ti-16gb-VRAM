#!/usr/bin/env python3
"""Render a preset template for your own machine.

Usage:
    python tools/render_preset.py presets/strata-512k-routed.json.template \
        --strata-root /path/to/Strata \
        --strata-data /path/to/Strata-data \
        --python /path/to/python.exe \
        --out strata-512k-routed.json

Placeholders replaced:
    ${STRATA_ROOT}   folder that contains engine-feed/, data/, run-*.bat
    ${STRATA_DATA}   folder that contains models/, packs/, dflash2/
    ${PYTHON}        Python 3.12 executable (must have nvidia cu13 DLLs in its site-packages)
    ${CUDA_DLL_DIR}  folder with the CUDA 13 runtime DLLs (nvidia/cu13/bin/x86_64)
    ${PORT}          API port (default 8080)
"""
import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("template", type=Path)
    ap.add_argument("--strata-root", required=True)
    ap.add_argument("--strata-data", required=True)
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--cuda-dll-dir")
    ap.add_argument("--port", default="8080")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    raw = args.template.read_text(encoding="utf-8")
    root = str(Path(args.strata_root).resolve()).replace("\\", "/")
    data = str(Path(args.strata_data).resolve()).replace("\\", "/")
    py = str(Path(args.python).resolve()).replace("\\", "/")
    nv = args.cuda_dll_dir or str(Path(py).parent / "Lib/site-packages/nvidia/cu13/bin/x86_64")

    for token, value in (
        ("${STRATA_ROOT}", root),
        ("${STRATA_DATA}", data),
        ("${PYTHON}", py),
        ("${CUDA_DLL_DIR}", str(nv).replace("\\", "/")),
        ("${PORT}", str(args.port)),
    ):
        raw = raw.replace(token, value)

    cfg = json.loads(raw)
    if cfg["args"] != cfg["args_written"]:
        raise SystemExit("refusing to write: args != args_written")
    cfg["port"] = int(args.port)
    args.out.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(f"  context      : {cfg['args'][cfg['args'].index('--max-context') + 1]}")
    print(f"  KV           : {cfg['args'][cfg['args'].index('--kv') + 1]}")
    print(f"  ring         : {cfg['env'].get('STRATA_PREFILL_RING')}")
    print(f"  routed stream: {cfg['env'].get('STRATA_PREFILL_ROUTED_STREAM')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
