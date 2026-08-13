$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
& "$PSScriptRoot\reset_hydradb.ps1"
& "$PSScriptRoot\start_hydradb.ps1"
python -m continuum.hydradb.health
if ($LASTEXITCODE -ne 0) { throw "HydraDB health check failed" }
python -m pytest -m hydradb -q
if ($LASTEXITCODE -ne 0) { throw "HydraDB integration tests failed" }
& "$PSScriptRoot\reset_hydradb.ps1"
Write-Output "PHASE 0 SMOKE PASS"
