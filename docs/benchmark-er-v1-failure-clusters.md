# Benchmark ER v1 — Failure Clusters (Phase 1)

Source run: `subset-20pct-baseline-001` (dev 80Q, full-v1 corpus, `--no-graph`).

**Classifier caveat:** coarse `ENTITY_RESOLUTION_FAILURE` labels are inflated when graph is disabled.
This doc uses trace fields (`retrieved_artifacts`, gold overlap) and question-text patterns.

- Dev questions: 80
- Failures analyzed: 72
- Retrieval OK but wrong answer: 28
- Retrieval miss (gold doc not retrieved): 44

## Pattern table

| Pattern | Count | % of failures | Example question_ids |
| --- | ---: | ---: | --- |
| project_names | 33 | 45.8 | qst_0003, qst_0031, qst_0037, qst_0043, qst_0050 |
| multi_entity_ambiguity | 21 | 29.2 | qst_0044, qst_0062, qst_0065, qst_0096, qst_0101 |
| company_alias | 20 | 27.8 | qst_0016, qst_0045, qst_0065, qst_0193, qst_0194 |
| temporal_owner | 15 | 20.8 | qst_0016, qst_0096, qst_0177, qst_0194, qst_0199 |
| pronouns | 9 | 12.5 | qst_0044, qst_0045, qst_0200, qst_0208, qst_0268 |
| other | 8 | 11.1 | qst_0067, qst_0128, qst_0133, qst_0134, qst_0146 |
| person_alias | 5 | 6.9 | qst_0061, qst_0156, qst_0234, qst_0289, qst_0339 |

## Top patterns covering 80%
Patterns: **project_names, multi_entity_ambiguity, company_alias** cover ≥80% of failure mentions.

## Retrieval vs resolution

| Bucket | Count |
| --- | ---: |
| Retrieval OK, answer wrong | 28 |
| Retrieval miss | 44 |
