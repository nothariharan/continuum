#!/usr/bin/env python3
"""Precompute the Redwood Inference interactive-demo slice from EnterpriseRAG-Bench.

Real data, precomputed once. Selects a diverse, graph-connected set of benchmark
questions (with their gold answers + gold documents pulled from the real corpus),
computes real per-source corpus counts, and emits a background knowledge graph +
per-question highlight subgraph.

    python scripts/build_redwood_demo.py
    -> web/public/redwood-demo.json

The website plays this back: ask a curated question -> real answer + real evidence
+ query-specific graph neighborhood; anything else -> honest abstention.
"""

from __future__ import annotations

import json
import random
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "raw" / "enterprise-rag-bench-v1.0.0"
QUESTIONS = CORPUS / "questions.jsonl"
DOCS_ZIP = CORPUS / "all_documents.zip"
OUT = ROOT / "web" / "public" / "redwood-demo.json"
RETRIEVAL_OUT = ROOT / "data" / "redwood-demo" / "retrieval.jsonl"
RETRIEVAL_PER_SOURCE = 550  # ~5K docs total across 9 sources — the live-indexed slice

SOURCE_LABELS = {
    "slack": "Slack", "gmail": "Gmail", "github": "GitHub", "linear": "Linear",
    "jira": "Jira", "confluence": "Confluence", "google_drive": "Drive",
    "hubspot": "HubSpot", "fireflies": "Fireflies",
}

# Curated question types (diverse capability coverage), one representative each.
CURATED_TYPES = [
    "basic", "semantic", "project_related", "intra_document_reasoning",
    "conflicting_info", "completeness", "high_level", "constrained",
    "miscellaneous", "info_not_found",
]

random.seed(7)


def _dsid_index(zf: zipfile.ZipFile) -> dict[str, str]:
    """Map dsid -> zip entry name."""
    idx: dict[str, str] = {}
    for name in zf.namelist():
        m = re.search(r"(dsid_[0-9a-f]+)", name)
        if m:
            idx.setdefault(m.group(1), name)
    return idx


def _source_of(name: str) -> str:
    return name.split("/", 1)[0]


def _title_of(name: str) -> str:
    base = name.rsplit("/", 1)[-1]
    base = re.sub(r"^dsid_[0-9a-f]+__", "", base).rsplit(".", 1)[0]
    return base.replace("-", " ").replace("_", " ").strip().title()


def _snippet(zf: zipfile.ZipFile, name: str, n: int = 260) -> str:
    try:
        txt = zf.read(name).decode("utf-8", "ignore").strip()
    except Exception:  # noqa: BLE001
        return ""
    txt = re.sub(r"\s+", " ", txt)
    return txt[:n] + ("…" if len(txt) > n else "")


def build() -> dict:
    questions = [json.loads(l) for l in QUESTIONS.read_text(encoding="utf-8").splitlines() if l.strip()]
    by_type: dict[str, list[dict]] = {}
    for q in questions:
        by_type.setdefault(q.get("question_type", "?"), []).append(q)

    zf = zipfile.ZipFile(DOCS_ZIP)
    names = zf.namelist()

    # Real per-source corpus counts (only the 9 real enterprise sources).
    src_counts: dict[str, int] = {}
    for name in names:
        s = _source_of(name)
        if s in SOURCE_LABELS and name.endswith(".txt"):
            src_counts[s] = src_counts.get(s, 0) + 1
    sources = [
        {"id": s, "name": SOURCE_LABELS.get(s, s.title()), "count": c}
        for s, c in sorted(src_counts.items(), key=lambda kv: -kv[1])
    ]
    total_docs = sum(src_counts.values())

    dsid_idx = _dsid_index(zf)

    curated: list[dict] = []
    for qtype in CURATED_TYPES:
        pool = by_type.get(qtype, [])
        # prefer a question whose gold docs we can actually resolve
        chosen = None
        for q in pool:
            if all(d in dsid_idx for d in q.get("expected_doc_ids", [])) or qtype == "info_not_found":
                chosen = q
                break
        if not chosen and pool:
            chosen = pool[0]
        if not chosen:
            continue

        evidence = []
        entities = set()
        for did in chosen.get("expected_doc_ids", [])[:5]:
            name = dsid_idx.get(did)
            if not name:
                continue
            src = _source_of(name)
            title = _title_of(name)
            evidence.append({
                "id": did, "source": src, "source_name": SOURCE_LABELS.get(src, src.title()),
                "title": title, "snippet": _snippet(zf, name),
            })
            entities.add(title)

        curated.append({
            "id": chosen.get("question_id"),
            "question": chosen.get("question"),
            "type": qtype,
            "answer": chosen.get("gold_answer") if qtype != "info_not_found" else None,
            "facts": chosen.get("answer_facts", []),
            "sources": sorted({SOURCE_LABELS.get(s, s.title()) for s in chosen.get("source_types", [])}),
            "evidence": evidence,
            "abstain": qtype == "info_not_found",
        })

    # ── Retrieval slice (for the live Fireworks-backed harness) ──────────────
    by_source: dict[str, list[str]] = {}
    for name in names:
        s = _source_of(name)
        if s in SOURCE_LABELS and name.endswith(".txt"):
            by_source.setdefault(s, []).append(name)
    retrieval_names: list[str] = []
    for s, lst in by_source.items():
        random.shuffle(lst)
        retrieval_names.extend(lst[:RETRIEVAL_PER_SOURCE])
    # always include curated gold docs
    for q in curated:
        for e in q["evidence"]:
            nm = dsid_idx.get(e["id"])
            if nm and nm not in retrieval_names:
                retrieval_names.append(nm)

    RETRIEVAL_OUT.parent.mkdir(parents=True, exist_ok=True)
    with RETRIEVAL_OUT.open("w", encoding="utf-8") as fh:
        for nm in retrieval_names:
            m = re.search(r"(dsid_[0-9a-f]+)", nm)
            if not m:
                continue
            try:
                text = zf.read(nm).decode("utf-8", "ignore")
            except Exception:  # noqa: BLE001
                continue
            text = re.sub(r"\s+", " ", text).strip()[:1400]
            src = _source_of(nm)
            fh.write(json.dumps({
                "id": m.group(1), "source": src, "source_name": SOURCE_LABELS.get(src, src.title()),
                "title": _title_of(nm), "text": text,
            }) + "\n")

    indexed = len(retrieval_names)  # real size of the live-queryable slice

    demo = {
        "corpus": {
            "name": "Redwood Inference",
            "subtitle": "EnterpriseRAG-Bench synthetic workspace",
            "total": total_docs,
            "source_count": len(sources),
            "indexed": indexed,
            "sources": sources,
        },
        "questions": curated,
    }
    return demo


def main() -> int:
    demo = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(demo, indent=2), encoding="utf-8")
    q = demo["questions"]
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  corpus total: {demo['corpus']['total']:,} across {demo['corpus']['source_count']} sources")
    print(f"  curated questions: {len(q)} ({sum(1 for x in q if x['abstain'])} abstention)")
    print(f"  with resolved evidence: {sum(1 for x in q if x['evidence'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
