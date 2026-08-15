# Phase 3 — Entity Resolution Design (research, not implementation)

Status: **design only**. Grounded in the actual identity signals of the
360-artifact sample (`data/extraction/mention_inventory.json`, 1,380
entries). No resolver code is written until claims extraction is
graph-grade (Gate 2) and this design is agreed with the teammate.

## 1. What the inventory actually contains

| signal | count (of 1,380) | notes |
|---|---:|---|
| person mentions | 705 | includes noise (see below) |
| ticket mentions | 307 | strong cross-source external IDs (e.g. INC-2026 in confluence+github+linear+slack) |
| email mentions | 242 | richest identity signal in the dataset |
| username mentions | 45 | slack handles |
| project / org | 42 / 39 | weak, role-heavy |

Identity-signal combos: 573 entries have **no** identity signal (first-name
or role-only), 426 carry `external_ids`, 380 carry emails. Only 1 entry has
both email and external_id — cross-signal fusion is rare and valuable.

Measured noise: mention precision is 0.71 (extraction metrics), and the
inventory confirms it — many "person" entries are email-body snippets
misclassified as person mentions (seen while labeling identity pairs).

## 2. Actual identity signals per person (examples)

- **Email families** (strongest): `Marcus Lin` → `marcus.lin@redwood.com`,
  `marcus_lin@redwood.ai`, `marcus_lin@redwood.com`; `Ben Carter` → 6
  variants across 4 Redwood domains. Local-part ≈ name is a near-certain
  same-person signal; dot/underscore variants are exact matches.
- **First-name-only mentions** (hardest): `Priya` (134 occurrences),
  `Maya` (121) — each is ambiguous across multiple full names (Priya Desai /
  Menon / Natarajan / Raman / Shah; Maya Patel / Maya Chen).
- **Cross-source overlap** (already flagged by the inventory): `Elena` ↔
  `lena`, `Sarah Liu` ↔ `Sara Liu`, `Liam Park` ↔ `Lina Park` (likely
  different — distinct names), `Marcus Lin` ↔ `marcus li`.
- **Customer-side vs Redwood-side**: emails like `samantha.holt@acmehealth.com`,
  `samira.k@fintechco.com`, `pdesai@medcord.com` are customer people;
  `@redwood.com` / `@redwood.ai` / `@redwood.inference.com` are employees.
  Domain is a strong differentiator.
- **Role-qualified mentions**: `Samira Patel (Redwood SE)`, `Maya (Redwood
  AE)` — role suffix is context, not identity; must be stripped.
- **Ticket/incident IDs**: `INC-2026`, `ADR-022`, `ENG-18428` — exact
  cross-source keys, trivial to resolve exactly.

## 3. Proposed pipeline (decided with the teammate before implementation)

```
Mention
  ↓ candidate blocking (normalized name token set, email local part,
  ↓  username, source user ID, ticket key prefix)
candidate pairs
  ↓ exact identity matches        (emails, usernames, source IDs — no fuzzy)
  ↓ fuzzy similarity              (name token Jaccard, edit distance on
  ↓                               local parts; only within blocked pairs)
  ↓ cross-source evidence         (same artifact set, co-occurrence,
  ↓                               frequency agreement)
  ↓ graph evidence                (shared claims/artifacts in HydraDB —
  ↓                               candidate lookup by key/alias)
  ↓ optional local LLM            (only for uncertain borderline cases;
  ↓                               LLM proposes, deterministic score decides)
score
  ↓
MERGE / REVIEW / SEPARATE / ABSTAIN
```

Rules of engagement, per AGENTS.md:

- **False merges are the critical failure mode.** Default to
  REVIEW/ABSTAIN when evidence is weak (first-name-only pairs).
- Deterministic signals (email local part, username, source ID, ticket key)
  decide before any fuzzy/LLM step.
- The resolver must be measurable on the Phase 3 eval set (below) and
  report precision/recall/abstain rates, with false-merge rate as the
  headline metric.
- Graph candidate lookup happens in HydraDB (see
  `docs/hydradb-query-shapes.md`); no client-side graph walking.

## 4. HydraDB constraints that shape the design

- `WHERE ... CONTAINS` is unsupported (only boolean combinations of
  property-equality predicates) → alias/external-ID lookup must use exact
  equality on indexed-style properties; plan a normalized `aliases`-style
  property per candidate, written at load time.
- Relationship-type and label parameters are unsupported → resolver
  queries are built from allowlists, same as the state engine.
- No list/map params → blocking lists arrive via UNWIND batch rows or
  per-candidate scalar queries.

## 5. Evaluation set (already built)

`data/labels/phase3-identity-pairs.jsonl` — **87 hand-labeled pairs**
(23 same / 21 different / 43 uncertain), each with the signals that justify
the verdict and a note. Generator: `scripts/build_identity_pairs.py`
(candidates pool in `data/labels/phase3-identity-candidates.jsonl`).

The set covers the real difficulty distribution: email-family same pairs,
distinct-people hard negatives (two Maya's, two Omar's, two Liam's), and the
first-name-only uncertain core. A resolver must report:
`same/different/uncertain` accuracy, abstain rate, and false-merge count —
on this set, from Day 1.

## 6. Explicit non-goals (until claims are graph-grade)

- No resolver implementation.
- No canonical entity schema beyond the existing key conventions.
- No full-corpus resolution (512K docs).
- No automatic merge into production-style state.
