# BATCH J — Final Benchmark (Founder-only)

Status: **OUT OF SCOPE for teammate implementation**

The teammate track stops before official EnterpriseRAG-Bench reruns.

## Founder responsibilities

- Verify scorer integrity (empty-answer bug, etc.)
- Create **new** run ID (never overwrite `full-v1-baseline-001`)
- Run 500Q / 512K (or agreed 100K subset) sequentially: BM25, Dense, Hybrid, GraphContinuum
- Same answer model, same scoring, checkpoint/resume enabled

## Teammate must NOT

- Modify `data/evals/benchmark-v1/checkpoints/`
- Change benchmark scoring or protocol without team agreement
- Run overnight benchmark until BATCH B–F stable and gold set 20/20

## Handoff checklist before BATCH J

- [ ] Live Slack ingestion stable (small channel)
- [ ] Query API + Slack bot demo working
- [ ] Cross-source E2E on live data
- [ ] 20/20 source→answer gold set
- [ ] No benchmark checkpoint diffs in teammate PRs
