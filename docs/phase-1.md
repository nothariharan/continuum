# Phase 1 — Synthetic Company Graph Harness

## Graph model

The fixture contains `Person`, `Project`, `Account`, `Artifact`, `Claim`, and `Source` nodes. Stable external identifiers are stored in each node’s `key` property because HydraDB requires non-negative integer graph IDs. `Claim` nodes are immutable records with subject, predicate, object, observed time, and validity fields.

Relationships used are `Person-[:OWNS]->Account/Project`, `Claim-[:ABOUT]->Entity`, `Claim-[:SOURCED_FROM]->Artifact`, `Artifact-[:FROM]->Source`, and `Claim-[:CONTRADICTS]->Claim`. Ownership edges retain `valid_from` and `valid_to`.

## Temporal behavior

Ownership transitions are stored as HydraDB relationship properties. The fixture represents an open-ended interval with the documented local sentinel `9999-12-31`; query results normalize that sentinel to `null`. The graph contains Arjun from July 1 through July 28 and Sarah from July 28 onward. Current and historical queries filter these graph-backed properties inside HydraDB.

## Claim behavior

The three Acme ownership claims coexist: Gmail reports Arjun, Linear records Sarah’s assignment, and Slack confirms the handoff. Claims are never overwritten by later evidence.

## Provenance behavior

The provenance query traverses `Claim -> Artifact -> Source` in HydraDB and returns claim IDs, artifact IDs, source names, kinds, and observed dates.

## Queries

- Q1 current Acme owner: Sarah Chen.
- Q2 Acme owner on 2026-07-15: Arjun Mehta; on 2026-08-13: Sarah Chen.
- Q3 provenance: Gmail, Linear, and Slack evidence with three claim IDs.
- Q4 conflict detection: Arjun and Sarah are conflicting claim subjects.
- Q5 absent query: StripeCo owner returns `status = ABSENT`.

## Performance

The generated baseline is stored in `docs/phase-1-benchmark.json` after running `python scripts/benchmark_phase1.py`. Values are environment-dependent and must be regenerated on the local HydraDB runtime.

| Query | p50 | p95 | p99 |
|---|---:|---:|---:|
| current_state | 2.490 ms | 4.797 ms | 21.303 ms |
| historical_state | 2.564 ms | 3.418 ms | 3.628 ms |
| provenance | 4.056 ms | 4.521 ms | 4.536 ms |
| conflict | 2.664 ms | 3.605 ms | 4.147 ms |

## HydraDB observations

HydraDB requires numeric graph identity IDs, supports parameterized OpenCypher, and supports batch writes through `UNWIND $rows`. Variable-length traversals require a fixed source ID. The loader therefore separates stable business keys from numeric graph IDs and uses fixed, documented query templates. No unsupported index or internal planner behavior is assumed.
