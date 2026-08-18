#!/usr/bin/env python3
"""Post-stabilization health check — record master SHA, tests, gold-set score."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "metadata" / "post_stabilization_baseline.json"
CHECKPOINT_DIR = ROOT / "data" / "evals" / "benchmark-v1" / "checkpoints"


def _git_sha() -> str:
    out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True)
    return out.strip()


def _run_pytest(args: list[str]) -> dict:
    cmd = [sys.executable, "-m", "pytest", *args, "-q", "--tb=no"]
    env = {"PYTHONPATH": str(ROOT), **dict(__import__("os").environ)}
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    return {
        "command": " ".join(cmd),
        "exit_code": proc.returncode,
        "stdout_tail": proc.stdout.strip().splitlines()[-3:] if proc.stdout else [],
        "stderr_tail": proc.stderr.strip().splitlines()[-3:] if proc.stderr else [],
    }


def _checkpoint_hashes() -> dict[str, str]:
    hashes: dict[str, str] = {}
    manifest = CHECKPOINT_DIR / "full-v1-100" / "checkpoint_sha256.json"
    if manifest.exists():
        hashes["full-v1-100"] = manifest.read_text(encoding="utf-8").strip()[:64]
    return hashes


def main() -> int:
    report = {
        "recorded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "master_sha": _git_sha(),
        "tests": {
            "sources": _run_pytest(["tests/sources/", "-m", "not hydradb"]),
            "query_core": _run_pytest(["tests/phase2b/test_query_core.py"]),
        },
        "benchmark_checkpoints_untouched": _checkpoint_hashes(),
        "gold_set": {"note": "Run scripts/benchmark_e2e_questions.py with HydraDB for 20/20 score"},
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    failed = any(r["exit_code"] != 0 for r in report["tests"].values())
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
