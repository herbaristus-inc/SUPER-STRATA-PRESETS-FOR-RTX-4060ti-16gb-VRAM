#requires -Version 5.1
<#
.SYNOPSIS
  Verifies the recovery kit without touching any hardware.
.DESCRIPTION
  Checks unlocker payload hashes, preset invariants and renderer importability.
  Safe to run on any machine, at any time.
#>
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$fail = 0

function Check([string]$label, [bool]$ok) {
  if ($ok) { Write-Host "  OK   $label" }
  else { Write-Host "  FAIL $label"; $script:fail++ }
}

Write-Host "== unlocker payload =="
$files = Join-Path $root 'boot-unlock\files'
$md = Get-Content (Join-Path $root 'boot-unlock\SHA256SUMS.md') -Raw
Get-ChildItem $files -File -Recurse | ForEach-Object {
  $rel = $_.FullName.Substring($files.Length).TrimStart('\').Replace('\','/')
  $hash = (Get-FileHash -Algorithm SHA256 $_.FullName).Hash.ToLowerInvariant()
  Check "$rel sha256" ($md -match [regex]::Escape("``$hash``"))
}
Check 'EFI bootloader present' (Test-Path (Join-Path $files 'EFI\BOOT\BOOTX64.EFI'))
Check 'payload size ~81 MB' ((Get-ChildItem $files -File -Recurse | Measure-Object Length -Sum).Sum -gt 80MB)

Write-Host "== presets =="
foreach ($name in @('strata-512k-routed.json.template','strata-1m-h4.json.template')) {
  $path = Join-Path $root "presets\$name"
  $cfg = Get-Content $path -Raw | ConvertFrom-Json
  $args = @($cfg.args)
  $written = @($cfg.args_written)
  Check "$name args==args_written" (($args -join '|') -eq ($written -join '|'))
  Check "$name KV int8" ($args[$args.IndexOf('--kv') + 1] -eq 'int8')
  Check "$name no max-tokens" ($args -notcontains '--max-tokens')
  Check "$name temperature 1" ($cfg.sampling.temperature -eq 1)
  Check "$name vision CPU" ($cfg.vision.gpu -eq $false)
  Check "$name DFlash2 draft" (($args -join ' ') -match 'dflash2')
  Check "$name fused prefill" ($cfg.env.STRATA_PF_FUSED -eq '1')
  Check "$name ring 512" ($cfg.env.STRATA_PREFILL_RING -eq '512')
  Check "$name routed stream" ($cfg.env.STRATA_PREFILL_ROUTED_STREAM -eq '1')
}
$one = Get-Content (Join-Path $root 'presets\strata-1m-h4.json.template') -Raw | ConvertFrom-Json
Check '1M tail-loan 0' ($one.env.STRATA_PREFILL_TAIL_LOAN -eq '0')
Check '1M headroom 4' ($one.env.STRATA_RESIDENT_HEADROOM_GIB -eq '4')
Check '1M context 1048576' (@($one.args)[@($one.args).IndexOf('--max-context') + 1] -eq '1048576')

Write-Host "== renderer =="
Check 'render_preset.py present' (Test-Path (Join-Path $root 'tools\render_preset.py'))
Check 'benchmark present' (Test-Path (Join-Path $root 'tools\prefill_real_bench.py'))

Write-Host ""
if ($fail) { throw "$fail check(s) failed. Do not continue recovery." }
Write-Host "ALL CHECKS PASSED. Recovery base kit is intact."
