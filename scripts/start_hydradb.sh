#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

state="${HYDRADB_STATE_DIR:-hydradb-data}"
name="${HYDRADB_CONTAINER_NAME:-continuum-hydradb}"
image="${HYDRADB_IMAGE:-ghcr.io/hydra-db/hydradb@sha256:db78309a233be54662db29744047e985a39b51c45a270d1a1f47c31a62cdb709}"
password="${HYDRADB_PASSWORD:-local-development-token-32-characters-long}"
bolt_port="${HYDRADB_BOLT_PORT:-7687}"
http_port="${HYDRADB_HTTP_PORT:-8443}"
admin_port="${HYDRADB_ADMIN_PORT:-9090}"
container_bolt=7687
container_http=8443
container_admin=9090

mkdir -p "$state/store" "$state/cache"
printf '%s' "$password" > "$state/auth-token"
mount="$(pwd)/$state:/data"

if docker ps -a --filter "name=^/${name}$" --format '{{.Names}}' | grep -qx "$name"; then
  docker rm -f "$name" >/dev/null
fi

if ! docker image inspect "$image" >/dev/null 2>&1; then
  docker pull "$image"
fi

docker run -d --name "$name" --user 0:0 \
  -p "${bolt_port}:${container_bolt}" -p "${http_port}:${container_http}" -p "${admin_port}:${container_admin}" \
  -v "$mount" \
  -e CLOUD_PROVIDER=local -e LOCAL_PATH=/data/store \
  -e GRAPH_NAMESPACE=default -e GRAPH_ID=default -e GRAPH_CELL_ID=cell-0 -e GRAPH_CELLS=cell-0 \
  -e GRAPH_NODE_ID=node-0 -e GRAPH_BOLT_NODE_ADDRESSES=node-0=127.0.0.1:${container_bolt} \
  -e GRAPH_ADVERTISED_BOLT_ADDR=127.0.0.1:${bolt_port} -e GRAPH_DATA_CACHE_DIR=/data/cache \
  -e GRAPH_AUTH_TOKEN_FILE=/data/auth-token -e GRAPH_ALLOW_PLAINTEXT=true \
  -e RUST_MIN_STACK=33554432 \
  "$image" >/dev/null

for _ in $(seq 1 120); do
  if curl -sf --max-time 2 "http://127.0.0.1:${admin_port}/readyz" >/dev/null 2>&1; then
    echo "HydraDB ready (bolt=${bolt_port}, admin=${admin_port})"
    exit 0
  fi
  sleep 0.5
done

docker logs "$name"
echo "HydraDB did not become ready on http://127.0.0.1:${admin_port}/readyz" >&2
exit 1
