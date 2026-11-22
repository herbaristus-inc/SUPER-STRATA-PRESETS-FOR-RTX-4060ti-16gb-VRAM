#!/usr/bin/env python3
"""Mirror the downloadable files into docs/downloads/ for GitHub Pages.

Run this from the repo root after changing any preset, launcher, result or tool:

    python tools/sync_docs_downloads.py

The landing page links to docs/downloads/ so it works both as a local file and
as a GitHub Pages site. This script keeps that folder in sync with the canonical
files at the repo root.
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "docs" / "downloads"

FILES = [
    ROOT / "presets" / "strata-512k-routed.json.template",
    ROOT / "presets" / "strata-1m-h4.json.template",
    ROOT / "launchers" / "run-512k-routed.bat.template",
    ROOT / "launchers" / "run-1m-h4.bat.template",
    ROOT / "launchers" / "README.md",
    ROOT / "tools" / "render_preset.py",
    ROOT / "tools" / "prefill_real_bench.py",
    ROOT / "docs" / "BOOT-ENV.md",
    ROOT / "results" / "README.md",
    ROOT / "tools" / "sync_docs_downloads.py",
]
FILES += sorted((ROOT / "results").glob("*.jsonl"))

DEST.mkdir(parents=True, exist_ok=True)
for src in FILES:
    name = src.name
    if src.name == "README.md":
        name = "LAUNCHERS-README.md" if src.parent.name == "launchers" else "RESULTS-README.md"
    shutil.copy2(src, DEST / name)
    print(f"synced {src.relative_to(ROOT)} -> docs/downloads/{name}")
