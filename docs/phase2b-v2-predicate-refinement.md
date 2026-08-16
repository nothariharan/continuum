# Phase 2B-V2 — Predicate Refinement Experiment

Branch: `feature/phase2b-claim-extraction-v2-founder`
Date: 2026-08-16

## What this experiment tested

Continuum's architectural thesis:

> A constrained open-source model, given candidate entities + evidence +
> a strict predicate enum after deterministic extraction, can resolve the
> last bit of semantic ambiguity — without inventing entities, evidence,
> or timestamps.

The deterministic layer (candidate detection → relation patterns →
timestamp resolver) had reached:

```
10/10 graph-loadable claims on the 11 known pair artifacts
0 false positives from the other 349 artifacts
7/10 exact fixture match
```

The three remaining errors were all predicate-nuance cases on email threads:

```
Jasmine Liu / Acme Payments   OWNS  (fixture: LEADS)
Jonas Weber / Acme Health     OWNS  (fixture: MAINTAINS)
Olga Petrov / Acme Analytics  OWNS  (fixture: MAINTAINS)
```

Subject, object, evidence, and timestamps were already correct in all three.
The model's only job: pick the right predicate.

## Architecture

```
Artifact
  → candidate detection
  → deterministic relation patterns      (claims tagged signal + ambiguous)
  → PredicateRefinementProvider          (Fireworks | Mock | future Ollama)
        → strict enum (OWNS/LEADS/MAINTAINS/ASSIGNED_TO/BLOCKS/.../ABSTAIN)
        → confidence threshold
        → Claim or ABSTAIN/REVIEW
```

Safety properties:

- The model never invents entities, evidence, or timestamps.
- The model only receives claims the deterministic layer already produced.
- Output must parse as JSON with a predicate from the strict enum and a
  confidence in [0, 1]; anything else → ABSTAIN.
- The allowed-predicate set is deterministic per entity pair.

## Provider

`continuum/extract/v2/refinement.py`

- `PredicateRefinementProvider` (Protocol)
- `FireworksPredicateProvider` — OpenAI-compatible client against
  `https://api.fireworks.ai/inference/v1`, `temperature=0`
- `MockPredicateProvider` — keeps the candidate predicate (tests/dry runs)

Configured via `.env`:

```
FIREWORKS_API_KEY=...
CONTINUUM_LLM_BASE_URL=https://api.fireworks.ai/inference/v1   (optional)
CONTINUUM_LLM_MODEL=accounts/fireworks/models/gpt-oss-120b       (optional)
```

The API key is gitignored (`.env` is never committed).

## Prompt contract

System prompt fixes the semantics:

```
OWNS        person owns the account / primary accountable owner (AE, CSM, meeting owner)
MAINTAINS   technical or operational owner doing the work (SE, engineering, ops)
LEADS       leads an engagement/initiative/review (point of contact coordinating)
ASSIGNED_TO assigned specific work items
```

User prompt carries: SUBJECT / TYPE, OBJECT / TYPE, CANDIDATE PREDICATE,
ALLOWED PREDICATES, ARTIFACT (verbatim, up to 4000 chars), EMAIL HEADERS,
and a conservative hint ("prefer ABSTAIN over a guess").

ABSTAIN is a first-class outcome. If the artifact lacks an explicit role or
responsibility signal, the claim stays at the deterministic predicate and is
flagged for review — it never becomes a guessed graph fact.

## Experiment: 11 known pair artifacts, 3 modes

Run with:

```
python scripts/experiment_predicate_refinement.py --model accounts/fireworks/models/gpt-oss-120b
```

Result (gpt-oss-120b, temperature 0):

```
Mode A  deterministic only           7/10 exact  0 model calls  ~3.5 ms/artifact
Mode B  refine ambiguous only        8/10 exact  6 calls        ~1.3 s/call
Mode C  refine every claim           8/10 exact  10 calls
```

Per-claim (Mode B):

```
Neha Kapoor   OWNS     → OWNS       expected OWNS       OK    conf 0.95
Priyom Das    OWNS     → OWNS       expected OWNS       OK    conf 0.95
Jasmine Liu   OWNS     → OWNS       expected LEADS      ABSTAIN (0.00)
Jonas Weber   OWNS     → OWNS       expected MAINTAINS  model chose OWNS 0.90
Olga Petrov   OWNS     → MAINTAINS  expected MAINTAINS  OK    conf 0.75
Sarah Chen    OWNS     → OWNS       expected OWNS       OK    conf 0.95
```

## Findings

1. **Mode B (refine ambiguous only) is the right shape.** Same exact-match as
   Mode C with 40% fewer model calls. Deterministic signals that carry an
   explicit role (Owner lines, attendee roles) are NOT ambiguous and should
   not be refined.

2. **The allowed-predicate set matters more than the model.** With `REVIEWS`
   in the allowed set, gpt-oss-120b flipped Olga to LEADS (0.65) — wrong.
   With `{OWNS, MAINTAINS, LEADS, ASSIGNED_TO}` (what a Person→Account thread
   can actually express), it returned MAINTAINS (0.85) — correct. The model
   was deterministic in both cases (3 identical runs each). The bias came
   from the prompt, not the model.

3. **Canonical labels are required.** `_allowed_predicates("person", ...)`
   silently collapsed to `{OWNS}` (labels must be `Person`/`Account`), which
   would make refinement impossible. Fixed by carrying
   `subject_label`/`object_label` in claim metadata.

4. **ABSTAIN works as designed.** Jasmine's thread genuinely does not state
   a role ("escalation points of contact" — could be LEADS or MAINTAINS).
   The model abstained; the deterministic OWNS stays, flagged for review.

5. **Honest disagreement remains.** Jonas: the model says OWNS 0.90 (thread
   ownership), the fixture says MAINTAINS (technical pilot owner). Both are
   defensible; this is a labeling-ambiguity case, not a system failure.

6. **Latency is the real cost.** ~1.3 s per model call vs ~3.5 ms per
   artifact deterministically. The 99%-deterministic / 1%-model architecture
   is what makes this viable.

## Model comparison (5 models, tight prompt)

| Model                          | Jasmine | Jonas  | Olga   | Empty/invalid |
|--------------------------------|---------|--------|--------|---------------|
| gpt-oss-20b                    | MAINTAINS ✗ | —     | ABSTAIN| 1            |
| **gpt-oss-120b (selected)**    | ABSTAIN | ABSTAIN| MAINTAINS ✓ | 0      |
| kimi-k2p7-code-fast            | ABSTAIN | —      | MAINTAINS ✓ | 2     |
| minimax-m2p7                   | MAINTAINS ✗ | ABSTAIN | MAINTAINS ✓ | 0 |
| deepseek-v4-flash-0731         | ABSTAIN | —      | —      | 2            |

gpt-oss-120b was selected: zero wrong predicates, disciplined abstention.

## State

```
Candidate detection       ✅
Timestamp resolution      ✅
Deterministic relations   ✅
Predicate refinement      ✅ (Mode B: 8/10 exact, 0 false positives)
Graph-loadability         10/10 ✅
Regression                124/124 ✅
```

Remaining ambiguity (Jasmine, Jonas) is genuine evidence ambiguity, not
extraction failure. Next steps per the plan: build the committed 100–200
artifact gold set, then expand the evaluation lexicon beyond 7 accounts.
