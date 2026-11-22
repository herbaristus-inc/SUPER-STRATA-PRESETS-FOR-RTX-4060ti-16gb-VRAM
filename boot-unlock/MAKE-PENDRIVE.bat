@echo off
title Build Strata unlock pendrive
cd /d "%~dp0"
echo.
echo  This will ERASE one USB disk and write the GPU unlock payload.
echo  Find the disk number with:  wmic diskdrive get index,model,size,mediatype
echo  or in PowerShell:  Get-CimInstance Win32_DiskDrive ^| select Index,Model,Size,MediaType
echo.
set /p DISK=Disk number to erase (example 2):
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0make_pendrive.ps1" -DiskNumber %DISK%
if errorlevel 1 pause
