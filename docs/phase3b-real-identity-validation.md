# Phase 3B — Real Identity Validation (teammate data consumed)

Branch: `feature/phase3b-real-identity-validation`
Date: 2026-08-16
Base: master (includes PR #3 identity-pair dataset + Phase 3A/3B machinery)

## What happened

1. Merged teammate PR #3 (`feature/entity-resolution-data` → master):
   103 identity pairs (27 SAME / 25 DIFFERENT / 51 UNCERTAIN) with
   FeatureVector-compatible features, schema validation, tests.
2. Built the consumption adapter: teammate's nested `a/b` JSONL format maps
   onto the founder `IdentityPair` contract (`cooccurrence` →
   `cooccurrence_score`), every row validated.
3. **Baseline** (untuned thresholds, all 103 pairs):

```
pair accuracy      0.8932
SAME      P/R/F1   1.0 / 0.778 / 0.875
DIFFERENT P/R/F1   0.885 / 0.92 / 0.902
FALSE MERGE RATE   0.0     ← critical metric: ZERO
FALSE SPLIT RATE   0.111
REVIEW rate        0.524   (conservative by design)
error taxonomy: FALSE_SPLIT_INITIALS 5, REVIEW_AMBIGUOUS 1,
                ABSTAIN_INSUFFICIENT_EVIDENCE 1, FALSE_SPLIT_USERNAME 1,
                FALSE_SPLIT_ALIAS 3
```

4. **Threshold calibration** (103 pairs, real resolver, sweep 0.80–0.97):

```
0.80  FM 0.25  (9)      ← unsafe
0.81–0.85  FM 0.036 (1) ← one false merge: 'Aisha' vs 'Aisha (PM)'
0.86–0.97  FM 0.0        ← safe zone
```

   Decision: **keep the 0.90 merge threshold** (already in the zero-false-
   merge zone). The 0.86–0.89 band is also safe but the current operating
   point is validated and conservative. The single 0.85-band false merge
   (`Aisha` vs `Aisha (PM)`, first name + role suffix, teammate-labeled
   UNCERTAIN) confirms why the threshold must not drop below 0.86.

5. **Held-out evaluation** (seed 42, 30% held out, frozen 0.90):

```
calibration (72): accuracy 0.875  FM 0.0  SAME_F1 0.849  DIFF_F1 0.882
evaluation (31):  accuracy 0.936  FM 0.0  SAME_F1 0.933  DIFF_F1 0.941
evaluation labels: 8 SAME / 15 UNCERTAIN / 8 DIFFERENT
```

   Note: 103 pairs is a small dataset — the held-out numbers carry wide
   error bars and are a methodological exercise, not a production benchmark.

6. **Real mention inventory** (1,126 mention-shaped entries):
   reproducible baseline — 87 clusters, max cluster 9, 247 mentions
   absorbed, 0 unsafe merges. Same as Phase 3B run (deterministic).

7. **Guards re-verified**: cross-org email (`david.park@redwood.com` vs
   `david.park@acme.com`) never merges (REVIEW); role mailboxes KEEP_SEPARATE;
   shared username REVIEW; same-name different-people KEEP_SEPARATE.

8. **Claim bridge**: 10 real claims → 5 partial (subject resolved), 5
   unresolved — honest about the inventory's account coverage gap. Unresolved
   mentions stay explicit (None), never guessed.

9. **Real entity→claim→graph fixture** (`scripts/entity_to_graph_fixture.py`):
   the cross-source soham identity story resolves end-to-end:

```
@soham (Slack) ─┐
soham-dev (GitHub) ─┼→ person:soham → claim "@soham OWNS Acme" → HydraDB
soham@company.com ─┘   → state: definitive Soham Ratnaparkhi (15ms)
                        → provenance: definitive, 1 evidence
```

10. **End-to-end question benchmark**: 20/20 (100%), p50 6.4ms, p95 18.6ms,
    p99 18.6ms — all categories (single/multi-hop, temporal, conflict,
    abstention, provenance, entity-resolution) green after integration.

## Artifacts

- `data/metadata/entity_resolution_real_eval.json` — baseline + taxonomy
- `data/metadata/entity_resolution_calibration_real.json` — operating curve
- `data/metadata/entity_resolution_heldout_eval.json` — split evaluation
- `data/metadata/entity_resolution_integration.json` — inventory run
- `data/metadata/entity_to_graph_fixture.json` — real vertical fixture
- `scripts/eval_entity_resolution_heldout.py` — seeded split evaluator

## What is NOT claimed

- Not "entity resolution solved" — 103 pairs is small; the UNCERTAIN-heavy
  distribution (51/103) reflects genuine enterprise ambiguity.
- Not production-ready — thresholds are validated on this dataset, not on
  the full corpus.
- The evaluation uses teammate labels through the founder contract; the
  founder resolver remains the system of record.

## Next steps (joint)

- Teammate: larger identity-pair set + feature coverage (embedding
  similarity currently 0% coverage).
- Founder: use calibration data for threshold tuning when the dataset grows;
  then the EnterpriseRAG-Bench comparison.
