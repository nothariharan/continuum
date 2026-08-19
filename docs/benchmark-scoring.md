# Benchmark scoring — versioned scorer

## Why versioned

The first benchmark run used a scorer with a bug that **inflated answer
correctness**: `score_answer(got, gold)` checked `got_n in gold_n`, and the
empty string is a substring of every string, so an **empty answer scored as
correct** for any non-empty gold answer.

To avoid silently rewriting history, the fix is versioned rather than
in-place:

| Function | Behavior | Used for |
|---|---|---|
| `score_answer_v1` | Legacy logic, preserved verbatim | Reproducing the original (inflated) number |
| `score_answer_v2` | Fixed logic (see below) | The official leaderboard (`score_rows`) |

`score_answer` remains as a backward-compatible alias to `score_answer_v1`,
so the existing analysis/audit scripts keep reproducing the old number until
they are explicitly migrated.

## What v2 changes

`score_answer_v2` differs from v1 in exactly two ways, both up front:

1. **Empty/whitespace `got` never passes** — `if not got_n: return False`.
   This closes the `"" in gold_n` bug: `score_answer_v2("", "Priya Nair")`
   is `False` (v1: `True`).
2. **Minimum informative answer** — empty and 1-character answers never pass
   (`if len(got_n) < 2: return False`).

Everything else is unchanged: exact match, substring match (either direction),
abstention symmetry, and 3+ token overlap at ≥0.6.

## Golden flips (v1 → v2)

| got | gold | v1 | v2 |
|---|---|---|---|
| `""` | `Priya Nair` | True | False |
| `"   "` | `anything at all` | True | False |
| `"a"` | `Acme Corp` | True | False |

## Audit note — `check_answer` (E2E)

The separate E2E scorer `scripts/benchmark_e2e_questions.py::check_answer` was
audited and does **not** have this bug: its substring check is
`normalize_answer(token) in got_n` (token against the *answer*), so an empty
answer cannot pass. It was left unchanged.
