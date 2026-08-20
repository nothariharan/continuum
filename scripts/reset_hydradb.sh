#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

"$(dirname "${BASH_SOURCE[0]}")/stop_hydradb.sh"

state_name="${HYDRADB_STATE_DIR:-hydradb-data}"
state="$(cd "$root" && cd "$state_name" 2>/dev/null && pwd || echo "$root/$state_name")"

case "$state" in
  "$root"/*) ;;
  *)
    echo "Refusing to reset state outside the Continuum workspace: $state" >&2
    exit 1
    ;;
esac

if [[ -d "$state" ]]; then
  rm -rf "$state"
fi

echo "Continuum HydraDB state reset: $state"
