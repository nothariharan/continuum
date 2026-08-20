"""Vercel Python serverless function — live Redwood harness.

Self-contained (no HydraDB, no continuum package import): BM25 retrieval over the
bundled EnterpriseRAG-Bench slice + a Fireworks answer. Same origin as the web
app, so no CORS wiring needed on the client.

GET  /api/redwood   -> {"status":"ok","indexed":N}
POST /api/redwood   {"question": "..."} -> {answer, abstain, evidence, sources, trace}
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import re
import time
from pathlib import Path

# ── Load the indexed slice + build BM25 once per cold instance ────────────────
_DATA = Path(__file__).with_name("_redwood_retrieval.jsonl")
_DOCS: list[dict] = []
if _DATA.exists():
    for _line in _DATA.read_text(encoding="utf-8").splitlines():
        if _line.strip():
            try:
                _DOCS.append(json.loads(_line))
            except Exception:  # noqa: BLE001
                pass


def _tok(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


_BM25 = None
try:
    if _DOCS:
        from rank_bm25 import BM25Okapi

        _BM25 = BM25Okapi([_tok(d.get("title", "") + " " + d.get("text", "")) for d in _DOCS])
except Exception:  # noqa: BLE001
    _BM25 = None

_MODEL = os.environ.get("CONTINUUM_LLM_MODEL", "accounts/fireworks/models/gpt-oss-20b")
_BASE_URL = os.environ.get("CONTINUUM_LLM_BASE_URL", "https://api.fireworks.ai/inference/v1")
_PROMPT = (
    "Answer the question using only the provided context. "
    "If the context is insufficient, respond with 'unknown - abstain'.\n\n"
    "Question: {q}\n\nContext:\n{c}\n\nAnswer:"
)


def _answer(question: str) -> dict:
    started = time.perf_counter()
    if not question.strip():
        return {"answer": None, "abstain": True, "evidence": [], "sources": [], "trace": {"error": "empty question"}}
    if not _BM25:
        return {"answer": None, "abstain": True, "evidence": [], "sources": [], "trace": {"error": "retrieval index unavailable"}}
    key = os.environ.get("FIREWORKS_API_KEY", "").strip()
    if not key:
        return {"answer": None, "abstain": True, "evidence": [], "sources": [], "trace": {"error": "FIREWORKS_API_KEY not set"}}

    t0 = time.perf_counter()
    scores = _BM25.get_scores(_tok(question))
    order = sorted(range(len(_DOCS)), key=lambda i: scores[i], reverse=True)[:6]
    top = [_DOCS[i] for i in order]
    retrieval_ms = (time.perf_counter() - t0) * 1000

    context = "\n\n".join(f"[{d.get('source_name')}] {d.get('title')}\n{d.get('text')}" for d in top)
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key, base_url=_BASE_URL, timeout=25.0, max_retries=1)
        g0 = time.perf_counter()
        resp = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": _PROMPT.format(q=question, c=context)}],
            temperature=0,
            max_tokens=512,
        )
        generation_ms = (time.perf_counter() - g0) * 1000
        ans = (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        return {"answer": None, "abstain": True, "evidence": [], "sources": [], "trace": {"error": f"generation failed: {exc.__class__.__name__}"}}

    low = ans.lower()
    abstain = (not ans) or low.startswith("unknown") or "abstain" in low or "not enough" in low or "insufficient" in low
    used = top[:4]
    evidence = [] if abstain else [
        {"id": d.get("id"), "source": d.get("source"), "source_name": d.get("source_name"),
         "title": d.get("title"), "snippet": (d.get("text") or "")[:220] + ("…" if len(d.get("text") or "") > 220 else "")}
        for d in used
    ]
    sources = [] if abstain else sorted({d.get("source_name") for d in used if d.get("source_name")})
    return {
        "answer": None if abstain else ans,
        "abstain": abstain,
        "evidence": evidence,
        "sources": sources,
        "trace": {
            "retrieval_ms": round(retrieval_ms, 1),
            "generation_ms": round(generation_ms, 1),
            "total_ms": round((time.perf_counter() - started) * 1000, 1),
            "candidates": len(top),
            "sources_searched": sorted({d.get("source_name") for d in top if d.get("source_name")}),
            "evidence_count": len(evidence),
        },
    }


class handler(BaseHTTPRequestHandler):
    def _send(self, obj: dict, code: int = 200) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send({}, 204)

    def do_GET(self) -> None:  # noqa: N802
        self._send({"status": "ok", "indexed": len(_DOCS)})

    def do_POST(self) -> None:  # noqa: N802
        n = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            question = json.loads(raw.decode("utf-8")).get("question", "")
        except Exception:  # noqa: BLE001
            question = ""
        self._send(_answer(str(question)))
