$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
& "$PSScriptRoot\stop_hydradb.ps1"
$stateName = if ($env:HYDRADB_STATE_DIR) { $env:HYDRADB_STATE_DIR } else { "hydradb-data" }
$state = Join-Path $root $stateName
$resolvedRoot = [IO.Path]::GetFullPath($root)
$resolvedState = [IO.Path]::GetFullPath($state)
if (-not $resolvedState.StartsWith($resolvedRoot + [IO.Path]::DirectorySeparatorChar)) { throw "Refusing to reset state outside the Continuum workspace: $resolvedState" }
if (Test-Path $resolvedState) { Remove-Item -LiteralPath $resolvedState -Recurse -Force }
Write-Output "Continuum HydraDB state reset: $resolvedState"
