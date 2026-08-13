$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$state = if ($env:HYDRADB_STATE_DIR) { $env:HYDRADB_STATE_DIR } else { "hydradb-data" }
$name = if ($env:HYDRADB_CONTAINER_NAME) { $env:HYDRADB_CONTAINER_NAME } else { "continuum-hydradb" }
$image = if ($env:HYDRADB_IMAGE) { $env:HYDRADB_IMAGE } else { "ghcr.io/hydra-db/hydradb:sha-6a2fbb192f37f51a93690a2ae2d2f5e27e6e4219" }
$password = if ($env:HYDRADB_PASSWORD) { $env:HYDRADB_PASSWORD } else { "local-development-token-32-characters-long" }
New-Item -ItemType Directory -Force "$state/store", "$state/cache" | Out-Null
Set-Content -NoNewline -Encoding ascii "$state/auth-token" $password
$mount = "{0}\{1}:/data" -f (Get-Location).Path, $state

$existing = docker ps -a --filter "name=^/$name$" --format "{{.Names}}"
if ($existing -eq $name) { docker rm -f $name | Out-Null }

docker pull $image
docker run -d --name $name --user 0:0 `
  -p 7687:7687 -p 8443:8443 -p 9090:9090 `
  -v $mount `
  -e CLOUD_PROVIDER=local -e LOCAL_PATH=/data/store `
  -e GRAPH_NAMESPACE=default -e GRAPH_ID=default -e GRAPH_CELL_ID=cell-0 -e GRAPH_CELLS=cell-0 `
  -e GRAPH_NODE_ID=node-0 -e GRAPH_BOLT_NODE_ADDRESSES=node-0=127.0.0.1:7687 `
  -e GRAPH_ADVERTISED_BOLT_ADDR=127.0.0.1:7687 -e GRAPH_DATA_CACHE_DIR=/data/cache `
  -e GRAPH_AUTH_TOKEN_FILE=/data/auth-token -e GRAPH_ALLOW_PLAINTEXT=true `
  -e RUST_MIN_STACK=33554432 $image | Out-Null

for ($i = 0; $i -lt 120; $i++) {
  try { if ((Invoke-WebRequest http://127.0.0.1:9090/readyz -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) { Write-Output "HydraDB ready"; exit 0 } } catch {}
  Start-Sleep -Milliseconds 500
}
docker logs $name
throw "HydraDB did not become ready on http://127.0.0.1:9090/readyz"
