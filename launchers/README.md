# Launchers

Two Windows `.bat` templates, one per shipped preset. They are a convenience, not a
requirement — the presets themselves are plain JSON, so any Strata Control invocation works.

**Yes, shipping launchers is common practice on GitHub** for local Windows LLM projects.
They are included here because the boot sequence is easy to get wrong, especially on the 1M
preset. They contain **no personal paths**: set `STRATA_ROOT`, `STRATA_DATA` and `PYTHON`
on your machine, then render the JSON with `tools/render_preset.py` before first launch.

```bat
set STRATA_ROOT=C:\path\to\strata
set STRATA_DATA=C:\path\to\Strata-data
set PYTHON=C:\path\to\python.exe
python tools\render_preset.py presets\strata-512k-routed.json.template ^
  --strata-root "%STRATA_ROOT%" --strata-data "%STRATA_DATA%" ^
  --python "%PYTHON%" --out "%STRATA_ROOT%\strata-512k-routed.json"
run-512k-routed.bat.template
```

Rename the `.template` file to `.bat` after copying it to your own folder. Control and
engine must both be **0.1.62** — other versions have different prefill env vars.

The 1M launcher does not warm up for you. Send 40k, then 256k, then the 1M request in the
same boot; a cold 1M request is how the `experts_native` illegal-access crash shows up.
