#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

"$(dirname "${BASH_SOURCE[0]}")/reset_hydradb.sh"
"$(dirname "${BASH_SOURCE[0]}")/start_hydradb.sh"
python3 -m continuum.hydradb.health
python3 -m pytest -m hydradb -q
"$(dirname "${BASH_SOURCE[0]}")/reset_hydradb.sh"
echo "PHASE 0 SMOKE PASS"
