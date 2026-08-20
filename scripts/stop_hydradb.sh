#!/usr/bin/env bash
set -euo pipefail

name="${HYDRADB_CONTAINER_NAME:-continuum-hydradb}"

if docker ps -a --filter "name=^/${name}$" --format '{{.Names}}' | grep -qx "$name"; then
  docker rm -f "$name" >/dev/null
fi

echo "HydraDB stopped"
