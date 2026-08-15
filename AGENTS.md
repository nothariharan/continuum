# Continuum — AGENTS.md

## 0. Purpose of This File

This file is the primary operating contract for AI coding agents working inside the Continuum repository.

Read this file before making changes.

Continuum is a long-term project with a one-year product vision, but development is intentionally phase-gated. Agents must work only on the active phase and must not jump ahead because a future feature appears architecturally interesting.

The current priority is correctness, reproducibility, and validation of the core system.

The project is being built by a two-person team:

- Founder / system owner: owns HydraDB, graph/state architecture, query layer, performance, system integration, and later MCP.
- Teammate / data owner: owns dataset processing, artifact normalization, retrieval experiments, mention extraction, claim extraction, evaluation, and later entity-resolution data work.

AI agents must respect this ownership boundary.

### 0.1 Agent Identity

Each AI agent session is assigned to exactly ONE subsystem. This note exists so agents never confuse their own subsystem with the teammate's.

**I am the founder / system-owner agent.** My working branch is `feature/phase2b-claims`. I own:

- HydraDB integration and graph schema
- claim ingestion into HydraDB
- state / temporal / conflict / provenance engines
- query layer and performance
- integration testing

I do NOT own (and must not touch without coordination):

- mention/claim extraction implementations (teammate)
- retrieval/embedding experiments (teammate)
- ground truth and extraction evaluation (teammate)

The shared data contract (`Artifact`, `Mention`, `Claim`) lives in `continuum/claims/schema.py`. I may define and lock it, but changes require team agreement. Extraction code that consumes the contract is the teammate's.

---

# 1. Product Definition

## 1.1 What Continuum Is

Continuum is a company-state and enterprise-context engine.

Its long-term purpose is to turn fragmented enterprise systems into a continuously updated, temporal, explainable model of organizational state.

The long-term conceptual pipeline is:

Enterprise systems
→ artifacts/events
→ normalized evidence
→ claims
→ entity resolution
→ ontology / relationships
→ temporal state
→ conflict resolution
→ provenance
→ queryable organizational state
→ MCP / API / web / agents

Continuum is NOT simply:

- a chatbot
- generic enterprise search
- a vector database
- a document store
- generic GraphRAG
- a UI over HydraDB
- an LLM that guesses answers from retrieved documents

The long-term thesis is:

> RAG tells you what the company said. Continuum tells you what the company currently knows, what used to be true, what changed, what conflicts, and why.

---

# 2. Hackathon Context

Continuum is being developed for Hack Hydra Track 01: Enterprise Context + Ontology.

The official problem asks teams to turn a large, messy enterprise corpus across multiple systems into a clean, queryable ontology and answer real questions against it.

The official Track 01 framing emphasizes:

- entity resolution
- ontology alignment
- multi-hop reasoning
- traceable graph paths
- correct abstention
- enterprise context across multiple systems

The project should remain compliant with the Track 01 problem while intentionally building a foundation capable of becoming a larger enterprise state platform.

Do not drift into Track 03 agent-memory architecture merely because MCP or persistent memory is useful later.

---

# 3. Long-Term One-Year Vision

The one-year product direction is:

## Layer 1 — Evidence

Enterprise source systems:

- Slack
- Gmail
- GitHub
- Linear
- Jira
- Google Drive
- HubSpot
- Fireflies
- Confluence
- future enterprise systems

↓

## Layer 2 — Claims

Atomic evidence-derived statements:

- Sarah OWNS Acme
- Ravi MAINTAINS payments-service
- Project X DEPENDS_ON Service Y

↓

## Layer 3 — Entity / Relationship Graph

Canonical people, projects, accounts, services, repositories, teams, decisions, etc.

↓

## Layer 4 — Resolved State

Current and historical state derived from claims, time, evidence, conflicts, and confidence.

↓

## Layer 5 — Delivery

- web application
- REST/API
- MCP
- SDKs
- agent integrations
- future automation

The full one-year roadmap is not the current implementation scope.

---

# 4. Core Architectural Principle

Continuum must maintain a strict separation between:

1. Evidence
2. Claims
3. Entities
4. Relationships
5. Resolved state
6. Explanation

Do not collapse these layers.

A source saying:

> "Sarah is taking over Acme"

is evidence.

A derived statement:

> Sarah OWNS Acme

is a claim.

The graph relationship:

> Sarah -OWNS-> Acme

is graph state.

The final answer:

> Current owner = Sarah

is resolved state.

The LLM explanation:

> "Sarah is the current owner because Linear and Slack confirm the handoff..."

is narration.

These are not interchangeable.

---

# 5. HydraDB Is a First-Class Dependency

The official HydraDB repository is a core project dependency and graph execution substrate.

Official repository:

https://github.com/hydra-db/hydradb

The HydraDB repository is currently included as a Git submodule.

Agents must treat the actual HydraDB repository and runtime behavior as the source of truth.

Do not assume undocumented capabilities.

Do not infer behavior solely from previous planning documents.

If HydraDB behaves differently from an architecture document, document the actual behavior and adapt Continuum around it.

---

# 6. HydraDB Architectural Philosophy

Continuum should use HydraDB for graph-native operations.

HydraDB must not be treated as a generic JSON/key-value database with graph labels.

Core graph traversal must happen inside HydraDB.

Do NOT:

- pull the graph into Python
- use NetworkX as the real traversal engine
- implement client-side BFS/DFS for core graph reasoning
- use the LLM to simulate graph traversal
- use HydraDB only as an artifact store

Preferred pattern:

semantic candidate retrieval
→ candidate entity IDs
→ HydraDB graph traversal
→ state resolution
→ provenance
→ explanation

HydraDB is responsible for the structural graph work.

---

# 7. HydraDB Integration Rules

When working with HydraDB:

1. Use the official local HydraDB runtime.
2. Use the thin Continuum HydraDB client.
3. Preserve the existing connection architecture.
4. Prefer parameterized queries.
5. Prefer batch writes.
6. Keep graph traversal inside HydraDB.
7. Respect actual HydraDB ID constraints.
8. Use stable Continuum business keys rather than leaking internal numeric graph IDs.
9. Validate query behavior against the actual engine.
10. Preserve reproducibility and reset workflows.

Known current constraint:

HydraDB requires numeric internal graph IDs in the current integration.

Therefore Continuum maintains stable business identifiers in `key`-style properties.

Application code should use Continuum stable identifiers rather than depending on internal numeric IDs.

---

# 8. Phase-Gated Development

The project is intentionally developed in phases.

Agents MUST NOT automatically proceed to the next phase.

A phase is complete only when its acceptance criteria pass.

Current progression:

Phase 0 — HydraDB bootstrap
COMPLETE

Phase 1 — Synthetic Continuum graph harness
COMPLETE

Phase 2A — Real Track 01 dataset reconnaissance / artifact harness
COMPLETE

Phase 2B — Real claims/evidence harness
CURRENT

Phase 3 — Entity resolution
NEXT AFTER PHASE 2B

Phase 4 — Temporal/conflict/state scaling

Phase 5 — Query/performance optimization at larger scale

Phase 6 — MCP

Phase 7 — Web interface

Later:
organizational impact
decision graph
simulation
agent infrastructure
enterprise deployment
etc.

---

# 9. Completed Work

## Phase 0

Completed:

- official HydraDB Git submodule
- local Docker lifecycle
- environment configuration
- thin Neo4j Bolt client
- health diagnostics
- smoke graph integration
- reset/reproducibility
- Makefile lifecycle commands
- Phase 0 documentation

HydraDB integration was verified against the real runtime.

---

# 10. Phase 1 Completed Work

The synthetic Continuum graph harness has been completed.

It includes:

- Person
- Project
- Account
- Artifact
- Claim
- Source
- current state
- historical state
- provenance
- conflict detection
- abstention

Current Phase 1 baseline:

- 6 Phase 1 integration tests passed
- clean reset/reseed passed
- p50 approximately 2.4 ms
- p95 approximately 4.2 ms
- p99 approximately 7.7 ms

These are historical synthetic baselines, not guaranteed targets for real data.

Do not break this regression baseline.

---

# 11. Phase 2A Completed Work

EnterpriseRAG-Bench v1.0.0 was selected as the Track 01 dataset.

Current dataset facts from the validated project state:

- approximately 512K documents
- nine enterprise sources
- reproducible dataset download
- SHA-verified release handling
- deterministic artifact normalization
- 360-document sample
- dataset inventory
- dataset quality report
- BM25 retrieval
- dense embedding retrieval
- hybrid RRF retrieval
- small real Artifact load into HydraDB
- zero read-back mismatches in the tested artifact load

Current experimental result:

BM25 currently outperforms dense embeddings on the 360-document retrieval sample at Recall@5.

This means:

DO NOT assume embeddings automatically replace lexical retrieval.

Retrieval must remain experimentally driven.

---

# 12. CURRENT PHASE — Phase 2B

The current phase is:

> Real enterprise artifacts → mentions → claims → small validated graph/state path.

The current objective is NOT:

- full dataset ingestion
- full graph engineering
- entity resolution at scale
- MCP
- UI
- production deployment
- full RAG
- complete ontology
- agent systems

The immediate goal is to validate that real enterprise evidence can be transformed into trustworthy claims.

---

# 13. Phase 2B Scope

Phase 2B includes:

- Mention extraction
- Claim extraction
- Human evaluation set
- Extraction precision/recall
- Claim schema
- Mention schema
- Artifact schema
- Small claim load into HydraDB
- Provenance
- Current state over manually resolvable entities
- Conflict tests on real claims
- Abstention tests
- Real-data query baseline
- Phase 1 regression

Phase 2B does not include automatic entity resolution yet.

---

# 14. Shared Data Contract

The teammate's pipeline must produce stable machine-readable structures.

Core shared objects:

Artifact
Mention
Claim

Minimum Claim fields:

- claim_id
- artifact_id
- subject_mention
- predicate
- object_mention
- observed_at
- valid_from
- valid_to
- confidence
- extraction_method

Do not require canonical entity IDs yet.

Mentions are intentionally unresolved until the entity-resolution phase.

Agents must not silently change the shared contract.

Changes to shared contracts require explicit team agreement.

---

# 15. Team Ownership Boundary

## Founder / system owner owns

- HydraDB
- graph schema
- claim ingestion into HydraDB
- state representation
- temporal model
- conflict handling
- provenance
- query layer
- query performance
- integration testing
- future MCP
- future system APIs

## Teammate / data owner owns

- dataset pipeline
- Artifact normalization
- Mention extraction
- Claim extraction
- retrieval experiments
- embedding experiments
- ground truth
- extraction evaluation
- retrieval evaluation
- future entity-resolution evidence generation
- data quality reporting

---

# 16. AI Agent Collaboration Rules

If you are an AI coding agent assigned to the founder's subsystem:

You MUST NOT:

- modify teammate extraction code without coordination
- redefine claim schemas silently
- modify retrieval logic to hide extraction failures
- create duplicate data contracts
- create an alternate dataset pipeline
- change the benchmark methodology without documentation
- add MCP
- add UI
- download/process the full dataset unless explicitly authorized
- perform automatic entity merges prematurely

If you are an AI coding agent assigned to the teammate subsystem:

You MUST NOT:

- redesign HydraDB graph semantics
- change the state engine
- modify temporal truth semantics
- change graph traversal architecture
- add MCP
- add UI
- change canonical graph IDs
- write directly into production-style graph state without the shared contract
- implement automatic identity merging before Phase 3

---

# 17. Git Workflow

Do not both work directly on master.

Recommended branches:

Founder:

feature/continuum-core

Teammate:

feature/phase2b-extraction

Master is the stable integrated branch.

Use small commits.

Good commit:

feat(graph): add real claim ingestion

Bad commit:

"finish continuum"

Before pushing:

- tests pass
- generated artifacts are understood
- schema is valid
- no unrelated files changed
- documentation updated when behavior changed

---

# 18. Collaboration Gates

## Gate 1 — Claim contract

Meet before large extraction work is merged.

Agree on:

- Artifact
- Mention
- Claim
- timestamp semantics
- source metadata
- provenance requirements

Then lock the contract.

---

## Gate 2 — First 50 real claims

Teammate produces 50 real claims.

Founder loads them into a temporary/test graph.

Both manually inspect:

raw artifact
→ normalized artifact
→ mention
→ claim
→ HydraDB
→ query
→ provenance

If this fails, STOP.

Do not scale.

---

## Gate 3 — Entity-resolution preparation

After claims and mentions are reliable:

teammate produces identity evidence.

Founder builds graph candidate lookup.

Together design entity resolution.

---

## Gate 4 — First full real question

Eventually:

question
→ entity resolution
→ retrieval
→ HydraDB
→ state resolver
→ provenance
→ structured answer

Only when this path is reliable should MCP work begin.

---

# 19. Retrieval Architecture

Continuum retrieval should follow this principle:

> Retrieval finds the starting neighborhood. HydraDB performs structural reasoning.

Preferred future architecture:

User question
→ intent / entity understanding
→ lexical retrieval
+
dense retrieval
→ candidate artifacts/entities
→ graph traversal
→ temporal/conflict filtering
→ state resolution
→ evidence selection
→ LLM explanation

Do not use:

vector similarity
→ final truth

Do not use:

LLM
→ arbitrary graph reasoning

---

# 20. LLM Architecture

The LLM is NOT the source of truth.

Use LLMs for:

- semantic extraction
- ambiguous entity resolution
- natural-language intent understanding
- answer explanation

Do NOT let the LLM directly decide:

- final permissions
- final state
- graph topology
- temporal validity
- conflict outcomes without evidence

Preferred pattern:

LLM proposes
→ deterministic/graph system verifies
→ state resolver returns result
→ LLM explains result

---

# 21. Local Model Strategy

The local-model experiment is encouraged because one important research/product hypothesis is:

> A small local model should become more useful when Continuum supplies the correct context.

For initial experiments, use a swappable LLM provider interface.

Do not hard-code Continuum around one model.

Potential experiments:

small local model + raw documents

small local model + naive retrieval

small local model + hybrid retrieval

small local model + Continuum structured context

stronger model + Continuum structured context

The purpose is to measure:

> How much model capability can Continuum replace with better context and state representation?

This is an experiment, not an assumption.

---

# 22. Current Immediate Roadmap

## Founder

Focus on:

1. Claim ingestion boundary
2. Real-claim HydraDB storage
3. Structured state query
4. Provenance
5. Conflict / abstention over real claims
6. Real-data graph benchmark

## Teammate

Focus on:

1. Mention extraction
2. Claim extraction
3. Human ground truth
4. Extraction precision/recall
5. Retrieval experiments
6. identity-signal inventory

## Collaboration

First 50 real claims
→ manual joint validation

Then:

entity-resolution design

Then:

first end-to-end real question.

---

# 23. What NOT to Build Now

Do not start:

- full 512K dataset ingestion
- full production graph
- full ontology
- advanced entity resolution
- vector database
- production MCP
- web UI
- enterprise authentication
- multi-tenancy
- live connectors
- impact simulation
- decision graph
- agent orchestration
- organizational prediction

These are future phases.

---

# 24. Phase 2B Acceptance Criteria

Phase 2B is complete only when:

- real artifacts have been manually evaluated
- mention extraction has measured precision/recall
- claim extraction has measured precision/recall
- Artifact/Mention/Claim contracts are locked
- real claims can be loaded into HydraDB
- provenance works
- current state works for manually resolvable real claims
- conflict detection works for a real sample
- abstention works
- real-data query latency is recorded
- Phase 1 regression remains green
- reset/reproducibility remains green

After this:

STOP.

Do not automatically progress.

---

# 25. Phase 3 Preview — Entity Resolution

The next difficult subsystem will be cross-source identity:

Example:

"Sam"
"@soham"
"S. Ratnaparkhi"
"soham-dev"
"soham@company.com"

Possible pipeline:

exact match
→ source IDs
→ email
→ username
→ fuzzy similarity
→ co-occurrence
→ graph evidence
→ optional model
→ merge/review/separate/abstain

Entity resolution must be measurable.

False merges are a critical failure mode.

---

# 26. Future State Model

Long-term Continuum separates:

Evidence
→ Claim
→ Entity
→ Relationship
→ Resolved State

Example:

Claim A:
Arjun owns Acme

Claim B:
Sarah owns Acme

Claim C:
Sarah owns Acme

Resolved state:

Sarah owns Acme
valid_from = July 28

The old claims remain.

History remains.

Provenance remains.

This is foundational to the company-state thesis.

---

# 27. Future Query Model

Long-term Continuum will expose semantic operations such as:

- resolve_entity
- get_current_state
- get_state_as_of
- get_history
- get_conflicts
- get_evidence
- get_dependencies
- get_impact

These will eventually be exposed through:

- Python/TypeScript APIs
- MCP
- web UI

The underlying logic must remain shared.

Do not duplicate business logic between MCP and the web application.

---

# 28. MCP Comes Before UI

When the core state engine is mature:

Core Continuum
→ semantic state API
→ MCP
→ AI agents

Only after MCP/API stability:

Core Continuum
→ web application

The web interface should be a client of Continuum, not a second implementation of Continuum.

---

# 29. Long-Term One-Year Vision

The one-year progression is approximately:

Months 1–3:
Evidence / claims / entity foundation
HydraDB graph/state
evaluation

Months 4–6:
Entity resolution
state API
MCP
impact traversal
change notifications

Months 7–9:
permissions
multi-tenancy
production connectors
reliability
data quality

Months 10–12:
decision graph
organizational dependency analysis
simulation
agent infrastructure
SDK/platform maturity

Future capabilities may include:

- company dependency analysis
- organizational risk
- decision history
- change subscriptions
- “what breaks if X leaves?”
- “what changed?”
- “what did we know at time T?”
- agent context APIs
- organizational simulation

But none of these are current-phase work.

---

# 30. Quality Rules

Prefer correctness over feature count.

Prefer deterministic behavior over opaque LLM behavior.

Prefer measured performance over assumed performance.

Prefer small validated slices over large unvalidated pipelines.

Prefer stable contracts over tightly coupled modules.

Prefer evidence over claims.

Prefer claims over guesses.

Prefer explicit abstention over hallucination.

Prefer HydraDB-native traversal over application-side graph walking.

Prefer reproducible experiments over demos that only work once.

---

# 31. Testing Rules

Every change should be validated at the smallest relevant level.

Unit test:

- schemas
- parsers
- normalizers
- state functions

Integration test:

- real HydraDB writes
- reads
- traversals
- claim loading
- provenance

Regression test:

- Phase 1 synthetic company

Evaluation test:

- extraction metrics
- retrieval metrics
- later entity-resolution metrics

Performance test:

- p50
- p95
- p99
- nodes touched
- edges traversed
- model latency
- retrieval latency

Never remove a failing test just to make the suite green.

---

# 32. Definition of “Done”

A phase is done when:

1. Its acceptance criteria pass.
2. Tests are reproducible.
3. Documentation exists.
4. The result is committed.
5. The stable branch remains green.
6. No hidden manual steps are required.
7. The next phase has not been silently started.

"Code exists" is not equivalent to "phase is done."

---

# 33. Final Mental Model for Agents

When working inside this repository, think:

We are not building a chatbot.

We are not building all of Continuum today.

We are building a sequence of validated layers:

Evidence
→ claims
→ entities
→ relationships
→ state
→ context
→ agents

Current focus:

Evidence
→ claims
→ HydraDB

The next hard problem after that:

Claims
→ entity resolution

The eventual product:

Resolved company state
→ humans + software + AI agents

Always work from the current phase.

Never skip validation.
