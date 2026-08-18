# PR #14 Review

Purpose:
: Query API seam (BATCH E) — transport-agnostic `QueryService` + optional
  FastAPI HTTP wrapper (`GET /health`, `POST /v1/ask`) + runner script.

Branch: `integration/query-api`
Base: `master`
Dependency: PR #10 (authoritative `continuum.benchmark.answer()` pipeline).
Files:
- `continuum/delivery/query_service.py` (27), `continuum/delivery/api.py` (42)
- `scripts/run_query_api.py` (22)
- `tests/delivery/test_query_service.py` (1 teammate test + 1 added in review)
- `pyproject.toml` (`delivery` extra: fastapi/uvicorn/slack-bolt/pydantic — all
  optional), `Makefile` (`test-delivery`, `run-query-api`)
Scope: delivery transport only.
Architecture boundary: correct target shape —
  `HTTP / Slack / MCP / Web → QueryService → authoritative query layer →
  graph/state/evidence → answer`.

**Seam verdict (the plan's central question):**

`QueryService.ask()` delegates to `continuum.benchmark.answer()`. Reviewed
deeply:

1. **It IS the exact existing production path.** `continuum/benchmark/__init__.py`
   `answer()` constructs `ContinuumPipeline` and runs the layered path
   (decompose → retrieval → entity resolution → traversal → state → evidence →
   answer). This is the same path PR #10 validated 17/20 and the gold-set
   runner uses. The benchmark runner is a *consumer* of this function, not a
   component of it.
2. **No benchmark-only behavior introduced.** Pipeline consumes only
   `question_id` + `question` (verified in `pipeline.py:161-169` and
   `decompose.py:226-227`); optional `evidence_entity`/`predicate`/`category`
   degrade to None for ad-hoc questions. No gold answers, no scoring, no
   manifest access, no benchmark semantics changed.
3. **Clean seam for later migration.** Consumers call `ask()`/`health()` only;
   moving `ask()` internals from `benchmark.answer()` to a future semantic
   query service requires zero consumer rewrites. Accepted as temporary seam,
   as the plan permits.

Validation:
- unit tests: 2/2 pass.
- API surface (manual, FastAPI TestClient):
  - `GET /health` → 200 `{status: ok, database}` ✓
  - `POST /v1/ask` valid JSON → 200, envelope passes through ✓
  - malformed request (missing `question`) → 422 ✓
  - non-JSON body → 422 ✓
  - conflict/absent status envelopes pass through unchanged ✓
  - empty body → 422, no secret leakage ✓
- live smoke: not run (HydraDB daemon down on this machine; will run in the
  cross-PR Phase 10 test).
- determinism: delegation test deterministic; pipeline determinism already
  established in PR #10.

Security:
- credentials: none in this PR; HydraDB client reads env at startup only.
- signatures: n/a (HTTP layer has no auth — documented as dev transport).
- secrets: none; audit clean.
- logs: uvicorn default access logs, no payload logging.

Data integrity:
- IDs: `question_id` echoes through; default `http-ad-hoc`.
- provenance: comes from the underlying pipeline (`evidence` chain), untouched
  by the transport.
- idempotency: n/a (stateless transport).
- duplicate behavior: n/a.

Regression:
- previous tests: full non-HydraDB suite — **277 passed, 68 deselected**
  (275 prior + 2 new), 0 failures.
- source→answer gold: untouched (no pipeline/query changes).
- benchmark artifacts: byte-identical (restored after suite side effect).

Review notes:
- **Defect found and fixed (committed `f8ee90d`, documented for teammate):**
  `continuum/delivery/api.py` declared `from __future__ import annotations`,
  so `body: AskRequest` became a string annotation; FastAPI could not resolve
  the closure-defined `AskRequest` from module globals and silently treated
  `body` as a *query parameter* → every valid `POST /v1/ask` returned
  422 `"Field required"`. Fix: removed the future-import from api.py (eager
  evaluation resolves the closure model). Regression test added.
- `@app.on_event("startup")` is deprecated in newer FastAPI but functional;
  `assert _service is not None` relies on asserts (stripped under `-O`) —
  minor, noted, not blocking.
- `delivery` extra installs cleanly; all deps verified importable.

Decision:
    MERGE

Reason:
The seam is thin, delegates to the authoritative single reasoning path, adds
no benchmark coupling or semantics changes, and can migrate to a semantic
query service without touching consumers. The transport defect that would have
broken every `POST /v1/ask` at runtime was caught by the gate and fixed with a
regression test.

Post-merge SHA: `b735ba2e1fe2b4f25b3901e1f82234caaa51edc9` (merge commit);
PR marked MERGED on GitHub (branch head `f8ee90d`).
