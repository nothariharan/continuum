"""Load official EnterpriseRAG-Bench question rows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from continuum.dataset.download import download_questions_jsonl

from .schema import DEFAULT_RAW


def load_official_questions(raw_dir: Path | None = None) -> list[dict[str, Any]]:
    path = download_questions_jsonl(raw_dir or DEFAULT_RAW)
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def sample_corpus_overlap(question: dict[str, Any], corpus_ids: set[str]) -> bool:
    return bool(set(question.get("expected_doc_ids") or ()) & corpus_ids)
