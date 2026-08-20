# Benchmark ER v1 — Failure Clusters (Graph dev run)

Source run: `subset-20pct-er-v1-dev-001` (dev 80Q, full-v1 corpus mode, graph enabled).

**Note:** Graph path does not perform BM25 corpus retrieval; most failures are retrieval misses (gold doc IDs absent from `retrieved_artifacts`).

- Dev questions: 80
- Failures analyzed: 77
- Retrieval OK but wrong answer: 0
- Retrieval miss (gold doc not retrieved): 76

## Pattern table

| Pattern | Count | % of failures | Example question_ids |
| --- | ---: | ---: | --- |
| project_names | 34 | 44.2 | qst_0003, qst_0031, qst_0037, qst_0043, qst_0050 |
| multi_entity_ambiguity | 24 | 31.2 | qst_0044, qst_0055, qst_0062, qst_0065, qst_0096 |
| company_alias | 21 | 27.3 | qst_0016, qst_0045, qst_0055, qst_0065, qst_0193 |
| temporal_owner | 16 | 20.8 | qst_0016, qst_0096, qst_0166, qst_0177, qst_0194 |
| other | 9 | 11.7 | qst_0001, qst_0067, qst_0128, qst_0133, qst_0134 |
| pronouns | 9 | 11.7 | qst_0044, qst_0045, qst_0200, qst_0208, qst_0268 |
| person_alias | 5 | 6.5 | qst_0061, qst_0156, qst_0234, qst_0289, qst_0339 |

## Top patterns covering 80%
Patterns: **project_names, multi_entity_ambiguity, company_alias** cover ≥80% of failure mentions.

## Retrieval vs resolution

| Bucket | Count |
| --- | ---: |
| Retrieval OK, answer wrong | 0 |
| Retrieval miss | 76 |
