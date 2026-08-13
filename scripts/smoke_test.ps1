$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
& "$PSScriptRoot\reset_hydradb.ps1"
& "$PSScriptRoot\start_hydradb.ps1"
python -m continuum.hydradb.health
python -m pytest -m hydradb -q
& "$PSScriptRoot\reset_hydradb.ps1"
Write-Output "PHASE 0 SMOKE PASS"

