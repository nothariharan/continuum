$ErrorActionPreference = "Stop"
$name = if ($env:HYDRADB_CONTAINER_NAME) { $env:HYDRADB_CONTAINER_NAME } else { "continuum-hydradb" }
if ((docker ps -a --filter "name=^/$name$" --format "{{.Names}}") -eq $name) { docker rm -f $name | Out-Null }
Write-Output "HydraDB stopped"

