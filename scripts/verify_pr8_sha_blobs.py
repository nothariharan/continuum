"""Checkpoint SHA manifest validation: disk vs git blob (line-ending check)."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

CK = Path("data/evals/benchmark-v1/checkpoints/full-v1-100")
sha = json.loads((CK / "checkpoint_sha256.json").read_text(encoding="utf-8"))

all_ok = True
for rel, expected in sorted(sha.items()):
    p = CK / rel
    disk = p.read_bytes()
    disk_lf = disk.replace(b"\r\n", b"\n")
    git_path = f"HEAD:{p.relative_to(Path('.'))}".replace("\\", "/")
    out = subprocess.run(["git", "cat-file", "blob", git_path], capture_output=True)
    if out.returncode != 0:
        print(f"[ERR ] {rel}: git cat-file failed: {out.stderr.decode(errors='replace')}")
        all_ok = False
        continue
    git_blob = out.stdout
    h_disk = hashlib.sha256(disk).hexdigest()
    h_lf = hashlib.sha256(disk_lf).hexdigest()
    h_git = hashlib.sha256(git_blob).hexdigest()
    print(f"{rel}")
    print(f"  disk-crlf: {h_disk}")
    print(f"  disk-lf  : {h_lf}")
    print(f"  git-blob : {h_git}")
    print(f"  expected : {expected}")
    if h_git == expected:
        print("  => git blob matches manifest (content intact in repo)")
        if h_disk != expected:
            print("  => disk differs: CRLF checkout artifact only")
    else:
        print("  => MISMATCH: git blob does NOT match manifest")
        all_ok = False

print()
print("RESULT:", "PASS - all blobs match manifest" if all_ok else "FAIL")
sys.exit(0 if all_ok else 1)
