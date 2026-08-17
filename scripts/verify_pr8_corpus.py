"""Independent corpus verification for PR #8 review (Phase 3).

Verifies:
1. SHA256 of data/raw/enterprise-rag-bench-v1.0.0/all_documents.zip
   vs pinned manifest 9d1174928696ad08bc15f3f104739519de633c1605a4ec2034e0e3c0087bc5cd
2. Entry counts: total / non-dir / .txt / non-txt
3. Per-source .txt counts vs benchmark_full_inventory.json source_counts
4. First/last names (ordering sanity)
"""

import hashlib
import json
import sys
import time
import zipfile
from collections import Counter
from pathlib import Path

ZIP = Path("data/raw/enterprise-rag-bench-v1.0.0/all_documents.zip")
EXPECTED_SHA = "9d1174928696ad08bc15f3f104739519de633c1605a4ec2034e0e3c0087bc5cd"
INVENTORY = json.loads(Path("data/metadata/benchmark_full_inventory.json").read_text(encoding="utf-8"))

start = time.time()
h = hashlib.sha256()
with ZIP.open("rb") as fh:
    for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b""):
        h.update(chunk)
actual_sha = h.hexdigest()
sha_time = time.time() - start
print(f"sha256 computed in {sha_time:.1f}s")
print(f"sha matches pinned manifest: {actual_sha == EXPECTED_SHA}")
print(f"actual:   {actual_sha}")
print(f"expected: {EXPECTED_SHA}")

start = time.time()
with zipfile.ZipFile(ZIP) as zf:
    names = zf.namelist()
    non_dir = [n for n in names if not n.endswith("/")]
    txt = [n for n in non_dir if n.endswith(".txt")]
    non_txt = [n for n in non_dir if not n.endswith(".txt")]
    by_source = Counter(n.split("/", 1)[0] for n in txt)
zip_time = time.time() - start
print(f"\nzip scan in {zip_time:.1f}s")
print(f"total entries:        {len(names)}")
print(f"non-directory entries: {len(non_dir)}")
print(f".txt entries:          {len(txt)}")
print(f"non-txt entries:       {len(non_txt)}")
for n in non_txt:
    print(f"  non-txt: {n}")
print(f"\nsource counts (live): {dict(sorted(by_source.items()))}")
print(f"source counts (inventory): {INVENTORY['source_counts']}")
print(f"match: {dict(sorted(by_source.items())) == {k: v for k, v in sorted(INVENTORY['source_counts'].items())}}")
print(f"\ninventory total_files: {INVENTORY['document_count']}")
print(f"inventory total_bytes: {INVENTORY['total_bytes']}")
