# Phase 3 Identity-Pairs Expanded Dataset — Status: SCAFFOLD (not gold)

**File:** `data/labels/phase3-identity-pairs-expanded.jsonl`

## What this file is

A **250-row scaffold** for the Phase 3 entity-resolution evaluation set.

- 87 rows carry original labels from `data/labels/phase3-identity-pairs.jsonl`
  (teammate-curated pairs).
- The remaining ~163 rows are **mechanically generated duplicates** of those
  base pairs with synthetic `pair_id`s (`-synthetic-N` suffix) and a
  `note` marker: `[synthetic scaffold - replace with labeled pair]`.

The scaffold was produced by `scripts/expand_identity_pairs_gold.py`, which
duplicates rows until the target count (default 250) is reached. The script's
docstring and every synthetic row's note field state this explicitly.

## What this file is NOT

- NOT 250 human-validated label pairs.
- NOT evaluation-ready gold data.
- The synthetic rows' labels are copies of base labels and **must not be used
  as independent ground truth** for entity-resolution evaluation.

## Rules

1. Do not quote "250 validated pairs" in any report or paper.
2. Do not run calibration/evaluation that reports precision/recall against
   the synthetic rows without treating them as copies of the 87 base pairs.
3. Before Phase 3 evaluation, replace synthetic rows with genuinely labeled
   pairs (human-reviewed) and remove the `synthetic` markers.
4. The test `tests/sources/test_identity_pairs_scaffold.py` enforces that
   every synthetic row remains visibly marked — keep it green.

## Label distribution (current scaffold)

| Label | Count |
|---|---|
| same | 58 |
| different | 63 |
| uncertain | 129 |
| **Total** | **250** |

(58 + 63 + 129 = 250; synthetic copies inflate these counts — see above.)
