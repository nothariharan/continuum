# PR Train Integration Baseline (Phase 0)

**Date:** 2026-08-18
**Repository:** nothariharan/continuum
**Branch:** master (local + origin verified)

---

## Master SHA

| Ref | SHA |
|---|---|
| Local master (checked out) | `5a0b738127b89e87b9ef266ca7604554d38f209d` |
| Origin master before push | `7995ecf0f2620ee7d9756bd195f7fcba77390a48` |

**Important:** local master is 4 commits ahead of origin/master. It contains the
PR #10 merge (`f3044c7`) plus the post-merge validation report (`5a0b738`).
PR #10 was reviewed in a prior session (B1–B4 stabilization, review gate
MERGE, full post-merge validation — see `docs/phase-source-to-answer-e2e-report.md`)
but the merge was **never pushed**. Origin still points at pre-#10 master.

Commit chain on local master:

```
5a0b738 docs(sources): post-merge validation report — master f3044c7, 17/20 E2E, blockers
f3044c7 merge: PR #10 source-to-answer E2E + B1-B4 stabilization (review gate: MERGE)
995e0a9 fix(sources): PR #10 stabilization — extraction quality, temporal validity, signal-driven entities, hermetic E2E
0e6ea4e feat(sources): prove Slack/Gmail fixture → extract → graph → answer E2E   <- PR #10 head
```

## Test Baseline (verified this session)

Command: `python -m pytest tests -q -m "not hydradb and not fireworks"`

| Metric | Result |
|---|---|
| Total tests | 264 passed |
| Deselected (hydradb/fireworks) | 68 |
| Failures | 0 |
| Duration | ~4m53s |

HydraDB-marked suites were verified in the prior session's post-merge
validation (78 sources+hydradb passed, phase1 6/6, phase2b spot 27/27) and
will be re-verified on master after each merge once Docker is available.

Note: `tests/eval/test_benchmark_mock_run.py` regenerates the tracked
`data/evals/benchmark-v1/reports/sample-v1/*.json` files on every run
(pre-existing behavior). These files are restored from HEAD after each suite
run and never committed.

## Source → Answer Gold (current)

| Metric | Result |
|---|---|
| Deterministic vertical (clean) | 17/20 |
| Deterministic vertical (polluted) | 17/20 |
| Known failures | se2e-04, se2e-12, se2e-14 (query-decomposition gaps in `continuum/query/decompose.py`, documented) |

## Benchmark Checkpoint Hashes (frozen, unchanged)

| Artifact | SHA-256 |
|---|---|
| `data/evals/benchmark-v1/checkpoints/full-v1-100/checkpoint_sha256.json` | `41D4DB47CC3DE8D3CFDADE09E1C49DA6C719D408158046821784522F5B7DE080` |
| `data/evals/benchmark-v1/checkpoints/full-v1-100/checkpoint_metadata.json` | `558FFBEE5C5222D6195AB6D6A0FCC726AD91D1E3DFF83719E0B174C1B931F434` |
| `data/evals/benchmark-v1/full-v1/questions.jsonl` | `98931206918B6B3DB32305AD61A6AC09DB0B1531444E33F8E3CE626F62910ACD` |
| `data/evals/benchmark-v1/sample-v1/questions.jsonl` | `C52318E6A67CCA19A9A4A86B41943579D8464D9EBA09C9A8D68DFFE53C74A499` |
| `data/evals/benchmark-v1/full-v1/manifest.json` | `5D2D84E3B937FD8CBD6B9D6BD228F57DB8A2F175275924DAAB629DA33FA086DA` |

These must remain byte-identical through the entire PR train.

## Working Tree State

- `git status --short` clean except pre-existing untracked files (leftover
  eval metadata, teammate report PDFs, execution plan HTMLs,
  `scripts/verify_pr9_determinism.py`) — none are part of this train and none
  will be committed.
- No secrets present in tracked files. `.env` is gitignored.

## Existing Open PRs (at baseline)

| PR | Title | Head branch | Base | State |
|---|---|---|---|---|
| #10 | feat(sources): prove Slack/Gmail fixture → extract → graph → answer E2E | `feature/source-extraction-e2e` | master | OPEN on GitHub; merged locally, pending push |
| #11 | post-stabilization health baseline gate (BATCH 0) | `integration/health-check-baseline` | master | OPEN, 1 commit, CLEAN vs old master |
| #12 | sync lifecycle and unified ingest orchestrator (BATCH B) | `integration/sync-lifecycle` | master | OPEN, 1 commit, CLEAN vs old master |
| #13 | live Slack ingestion and events gateway (BATCH C) | `integration/slack-live` | master | OPEN, 1 commit, CLEAN vs old master |
| #14 | query API seam delegating to benchmark answer() (BATCH E) | `integration/query-api` | master | OPEN, 1 commit, CLEAN vs old master |
| #15 | Slack query bot with Socket Mode dev runner (BATCH F) | `integration/slack-bot` | **integration/query-api** | OPEN, 1 commit, stacked on #14 |
| #16 | Gmail live ingestion scaffold (BATCH D) | `integration/gmail-live-scaffold` | master | OPEN, 1 commit, CLEAN vs old master |
| #17 | event queue dedup and expanded ER gold scaffold (BATCH H+G) | `integration/events-queue` | master | OPEN, 1 commit, CLEAN vs old master |

**Stacking observation:** all #11–#17 branches are based on pre-#10 master
(`7995ecf`). None contains PR #10's stabilization work. Each branch must be
updated against new master (post-#10) before merge, and re-tested.

## Plan

1. Push local master (with PR #10) to origin.
2. Review/update/merge #11 → #12 → #13 → #14 → #15 → #16 → #17 in dependency
   order, one at a time, with per-PR reports in `docs/integration/pr-XX-review.md`.
3. Full master validation + cross-PR continuous memory test.
4. Final report `docs/integration/pr-train-final-report.md`.
