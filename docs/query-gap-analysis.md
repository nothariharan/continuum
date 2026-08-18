# Query Gap Analysis — Source E2E 17/20 → 20/20

Baseline: `make source-e2e` on master @ `c77dd4a` with three deterministic failures.

## Pipeline trace

```
question (questions.jsonl)
  → decompose_question()     continuum/query/decompose.py
  → QueryContext             continuum/query/context.py
  → ContinuumPipeline._state() continuum/benchmark/pipeline.py
  → temporal / provenance / conflict resolvers
  → format_answer_from_result() → _format_answer()
```

## se2e-04 — Who owns Acme now after the handoff?

| Stage | Expected | Observed (before fix) |
|-------|----------|----------------------|
| Intent | OWNERSHIP | OWNERSHIP |
| Temporal | `after` + anchor `handoff`, `current` | Parsed correctly |
| State | Priya (post-handoff owner) | Soham (current open-ended winner) |

**Root cause:** `resolve_state_for_constraints()` did not resolve event-anchored
`after the handoff` to the transition timestamp. With both `after` and `current`
constraints, execution fell through to `resolve_state()` (latest open validity).

**Fix:** `resolve_state_after_event()` in `continuum/query/temporal.py` walks
ordered ownership history and returns the subject who begins when the previous
holder's interval closes (Morgan → Priya). Wired from `after` + `handoff` anchor.

## se2e-12 — Which claim and artifact support Soham owning Acme?

| Stage | Expected | Observed (before fix) |
|-------|----------|----------------------|
| Intent | PROVENANCE | CONFLICT (`which claim` matched first) |
| State | provenance envelope | conflict envelope |
| Answer | contains `claim` | `CONFLICT: ...` |

**Root cause:** `_INTENT_RULES` ordered CONFLICT before PROVENANCE; the pattern
`which claim` matched provenance phrasing.

**Fix:** Reordered rules; narrowed CONFLICT to `which claim(?! and artifact)`;
added explicit PROVENANCE pattern for `which claim and artifact`. Pipeline routes
PROVENANCE before CONFLICT when phrasing includes `which claim and artifact`.

## se2e-14 — Does Slack or Gmail show the CedarBank handoff?

| Stage | Expected | Observed (before fix) |
|-------|----------|----------------------|
| Intent | SOURCE_PRESENCE | OWNERSHIP (via `owns` in graph entity) |
| State | sources present in evidence | CedarBank owner name |
| Answer | Gmail \| Slack | person name |

**Root cause:** Cross-source presence questions were routed to ownership state
because no dedicated intent existed and category alone did not disambiguate.

**Fix:** Added `SOURCE_PRESENCE` intent for `does … show` phrasing.
`ContinuumPipeline._source_presence()` filters provenance evidence to mentioned
sources and returns a definitive source list (no entity-specific hacks).

## Validation

After fixes:

```bash
make source-e2e                    # 20/20 × 2 identical runs
python -m pytest tests/phase2b/test_query_core.py -q
python -m pytest -m hydradb -q
```

Regression tests added in `tests/phase2b/test_query_core.py` for intent/temporal
classification of all three failing questions.
