#requires -RunAsAdministrator
<#
.SYNOPSIS
  Builds the boot pendrive that unlocks the RTX 4060 Ti tensor-core PLL.

.DESCRIPTION
  Wipes ONE removable USB disk, creates a single active FAT32 partition and
  copies the files from .\files onto it. Nothing else is touched.

  The script refuses to continue unless you pass -DiskNumber explicitly and
  confirm the model/size shown on screen. It never targets a fixed drive
  letter and it never writes to a fixed disk.

.EXAMPLE
  .\make_pendrive.ps1 -DiskNumber 2
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]
  [ValidateRange(0,99)]
  [int]$DiskNumber,

  [switch]$SkipConfirm
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$src  = Join-Path $here 'files'

if (-not (Test-Path (Join-Path $src 'EFI\BOOT\BOOTX64.EFI'))) {
  throw "Payload not found at $src. Clone the whole repo first."
}

$disk = Get-CimInstance Win32_DiskDrive -Filter "Index = $DiskNumber"
if (-not $disk) { throw "Physical disk $DiskNumber not found." }
if ($disk.MediaType -notmatch 'Removable') {
  throw "Disk $DiskNumber is '$($disk.MediaType)', not Removable. Refusing to touch it."
}
if ($disk.Size -lt 512MB) { throw "Disk $DiskNumber is smaller than 512 MB." }

Write-Host "TARGET DISK  : $($disk.DeviceID)"
Write-Host "MODEL        : $($disk.Model)"
Write-Host "SIZE         : $([math]::Round($disk.Size/1GB,2)) GB"
Write-Host "PAYLOAD      : EFI\BOOT\BOOTX64.EFI + 8 files, ~81 MB"
Write-Host ""
Write-Host "ALL DATA ON THIS DISK WILL BE ERASED."

if (-not $SkipConfirm) {
  $answer = Read-Host "Type ERASE to continue (anything else aborts)"
  if ($answer -ne 'ERASE') { Write-Host "Aborted."; exit 2 }
}

#diskpart script: clean only the chosen disk, one active FAT32 partition
$dp = @"
select disk $DiskNumber
clean
create partition primary
select partition 1
active
format fs=fat32 quick label=UNLOCK
assign
exit
"@
$tmp = Join-Path $env:TEMP "strata-unlock-diskpart-$PID.txt"
$dp  | Set-Content -Encoding ASCII -Path $tmp
try {
  & diskpart.exe /s $tmp | Out-Host
  if ($LASTEXITCODE -ne 0) { throw "diskpart failed with exit code $LASTEXITCODE" }
} finally {
  Remove-Item -Path $tmp -Force -ErrorAction SilentlyContinue
}

# locate the volume now mounted from that partition
$part = Get-CimInstance Win32_DiskPartition |
  Where-Object { $_.DiskIndex -eq $DiskNumber -and $_.Type -like 'GPT:Installable*' -or ($_.DiskIndex -eq $DiskNumber -and $_.Type -eq 'Removable') } |
  Select-Object -First 1
if (-not $part) { $part = Get-CimInstance Win32_DiskPartition | Where-Object DiskIndex -eq $DiskNumber | Select-Object -First 1 }
$vol = Get-CimInstance Win32_LogicalDiskToPartition |
  Where-Object { $_.Antecedent.DeviceID -eq $part.DeviceID } |
  ForEach-Object { Get-CimInstance Win32_LogicalDisk -Filter "DeviceID = '$($_.Dependent.DeviceID)'" }

if (-not $vol) { throw "Could not resolve the mounted volume after formatting." }
$dest = $vol.DeviceID
Write-Host "Mounted as $dest"

Copy-Item -Path (Join-Path $src '*') -Destination "$dest\" -Recurse -Force

# verify every payload file byte-for-byte
$bad = @()
Get-ChildItem -Path $src -File -Recurse | ForEach-Object {
  $rel = $_.FullName.Substring($src.Length).TrimStart('\')
  $target = Join-Path $dest $rel
  if (-not (Test-Path $target)) { $bad += "MISSING $rel"; return }
  $a = (Get-FileHash -Algorithm SHA256 $_.FullName).Hash
  $b = (Get-FileHash -Algorithm SHA256 $target).Hash
  if ($a -ne $b) { $bad += "MISMATCH $rel" }
}
if ($bad.Count) { throw "Verification failed:`n$($bad -join "`n")" }

Write-Host ""
Write-Host "DONE. Pendrive $dest is ready."
Write-Host "Boot from it, press SPACE at the unlocker banner, then boot Windows again."
Write-Host "Check the unlocker log on the pendrive for plm_open=true."
