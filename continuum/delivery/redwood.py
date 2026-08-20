"""Redwood Inference live harness — retrieval + Fireworks answer over a real
EnterpriseRAG-Bench slice.

Anyone can ask an arbitrary question: BM25 retrieves from the indexed slice, and
the shared Fireworks answer model generates a grounded answer with real timings.
Falls back to honest abstention when the model can't support an answer.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from continuum.embed.bm25 import BM25Retriever

ROOT = Path(__file__).resolve().parents[2]
RETRIEVAL_PATH = ROOT / "data" / "redwood-demo" / "retrieval.jsonl"

_ABSTAIN_RE = re.compile(
    r"\b(?:i (?:do not|don't) have|not enough (?:information|evidence)|cannot (?:find|determine|answer)"
    r"|no (?:information|evidence|mention)|unable to (?:find|answer)|not (?:found|available|mentioned))\b",
    re.IGNORECASE,
)


class RedwoodHarness:
    def __init__(self, path: Path | None = None) -> None:
        self.docs: list[dict[str, Any]] = []
        p = path or RETRIEVAL_PATH
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self.docs.append(json.loads(line))
        self._corpus = [f"{d.get('title','')} {d.get('text','')}" for d in self.docs]
        self._bm25 = BM25Retriever(self._corpus) if self._corpus else None
        self._model = None  # lazy Fireworks client

    def _answer_model(self):
        if self._model is None:
            from continuum.eval.benchmark.answer_model import RealAnswerModel

            self._model = RealAnswerModel()
        return self._model

    def ask(self, question: str, top_k: int = 6) -> dict[str, Any]:
        started = time.perf_counter()
        if not self._bm25:
            return {"answer": None, "abstain": True, "evidence": [], "sources": [],
                    "trace": {"error": "retrieval slice not built (run scripts/build_redwood_demo.py)"}}

        t0 = time.perf_counter()
        hits = self._bm25.search(question, top_k=top_k)
        retrieval_ms = (time.perf_counter() - t0) * 1000
        top = [self.docs[i] for i, _ in hits]

        context = "\n\n".join(f"[{d['source_name']}] {d['title']}\n{d['text']}" for d in top)
        try:
            answer, _tokens, generation_ms = self._answer_model().generate(question, context)
        except Exception as exc:  # noqa: BLE001
            return {"answer": None, "abstain": True, "evidence": [], "sources": [],
                    "trace": {"error": f"generation unavailable: {exc.__class__.__name__}"}}

        low = answer.strip().lower()
        abstain = bool(_ABSTAIN_RE.search(answer)) or not answer or low.startswith("unknown") or "abstain" in low
        used = top[:4]
        evidence = [
            {"id": d["id"], "source": d["source"], "source_name": d["source_name"],
             "title": d["title"], "snippet": d["text"][:220] + ("…" if len(d["text"]) > 220 else "")}
            for d in used
        ]
        sources = sorted({d["source_name"] for d in used})
        total_ms = (time.perf_counter() - started) * 1000
        return {
            "answer": None if abstain else answer,
            "abstain": abstain,
            "evidence": [] if abstain else evidence,
            "sources": [] if abstain else sources,
            "trace": {
                "retrieval_ms": round(retrieval_ms, 1),
                "generation_ms": round(generation_ms, 1),
                "total_ms": round(total_ms, 1),
                "candidates": len(hits),
                "sources_searched": sorted({d["source_name"] for d in top}),
                "evidence_count": 0 if abstain else len(evidence),
            },
        }


_HARNESS: RedwoodHarness | None = None


def get_harness() -> RedwoodHarness:
    global _HARNESS
    if _HARNESS is None:
        _HARNESS = RedwoodHarness()
    return _HARNESS
