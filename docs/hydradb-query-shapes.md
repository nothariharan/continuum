# HydraDB Query Shapes — Research Notes for Phase 3 and State Queries

Status: **documented and measured on the small graph** (360 artifacts + real
claim fixture). No optimization performed. Full latency table:
`docs/hydradb-query-shape-measurements.json`; repro:
`python scripts/measure_query_shapes.py`.

## 1. Query shapes needed

| shape | query pattern | works? | p50 |
|---|---|---|---|
| candidate by exact key | `MATCH (n {key: $key})` | yes | 4.9 ms |
| candidate by name | `MATCH (n:Person {name: $name})` | yes | 3.0 ms |
| candidate by external ID / alias | `MATCH (n) WHERE n.aliases CONTAINS $alias` | **no** | — |
| claims involving entity | `MATCH (c:Claim {subject_id: $key})` | yes | 3.0 ms |
| claims about entity | `MATCH (c:Claim {object_id: $key})` | yes | 3.4 ms |
| conflicting claims | `MATCH (a:Claim {..})-[:CONTRADICTS]->(b:Claim)` | yes | 4.3 ms |
| current owner | `(s)-[r:OWNS]->(o {key}) WHERE r.valid_to = open` | yes | 3.1 ms |
| prior owner | `WHERE r.valid_to <> open` | **no** (parse error on `<>`) | — |
| reverse dependencies | `(s)-[:DEPENDS_ON]->(o {key})` | yes | 6.2 ms |
| claim → artifact → source | `(c)-[:SOURCED_FROM]->(a)-[:FROM]->(s)` | yes | 4.2 ms |
| predicate counts | `RETURN c.predicate, count(*)` | yes | 2.6 ms |
| two-hop shared artifacts | `(c)-[:SOURCED_FROM]->(a)<-[:SOURCED_FROM]-(d)` | yes | 5.1 ms |

## 2. Findings that change the design

1. **No `CONTAINS` in WHERE** — HydraDB supports only boolean combinations
   of property-equality predicates. Alias/external-ID candidate lookup must
   be exact equality. Consequence for Phase 3: write a normalized
   `aliases`-style property (pipe-joined) at load time and query with
   equality, or maintain an app-side blocked index per identity family.
2. **No `<>` inequality** — prior-owner queries must use `r.valid_to <
   $open` (or an equivalent supported form). Validate against the engine
   before relying on it.
3. **Label-less MATCH rejected** — every traversal endpoint needs a label
   (Phase 2B already encodes this).
4. **No list/map params** — candidate blocking lists arrive via UNWIND
   batch rows or per-candidate scalar queries.
5. **Two-hop traversals work** and are cheap at this scale (5.1 ms) — the
   co-occurrence graph (claims sharing an artifact) is available to Phase 3
   without new schema.

## 3. What will need attention at scale (do not build yet)

- **Property index on `key`/`subject_id`/`object_id`/`aliases`** — every
  state query enters through one of these equality predicates; at 512K
  artifacts with millions of claims, unindexed scans will dominate. Verify
  HydraDB index support (CREATE INDEX) against the runtime before Phase 5.
- **Reverse edges** — `prior owner`, `reverse dependencies`, and
  `who changed X` are all inbound traversals; consider explicit reverse
  relationship types only if measurements justify it.
- **Bounded traversal** — multi-hop impact queries need hop limits and
  path counts; confirm `LIMIT` behavior on the engine.
- **Batching** — bulk claim ingestion already chunks (Phase 2A/2B); the
  same batching applies to candidate-write operations during resolution.
