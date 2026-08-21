# Continuum: The 6 Core Technical Foundations & Architecture

> **Document Version:** 1.0  
> **Project:** `Continuum` (Enterprise Bitemporal Truth Engine)  
> **Source Material:** Agent Group 9–14 Core Technical Deep-Dive Stream  
> **Substrate Engine:** HydraDB Engine (RAM Hot Tier, NVMe CSR/CSC Warm Tier, S3 Parquet Cold Tier)  

---

## Executive Summary & Architectural Core

Enterprise AI agents fail in production not because LLMs lack reasoning power, but because underlying context infrastructures treat knowledge as a flat, unversioned, identity-naive vector database. When corporate data is fractured across disparate platforms (Slack, Jira, Linear, GitHub, Gmail, HubSpot, Fireflies), it introduces **aliases, out-of-order temporal state changes, direct contradictions, unverified claims, missing provenance, and security authorization leaks**.

HydraDB addresses this by building a **graph-native context infrastructure**. To achieve production-grade performance while operating 10x cheaper on Object Storage, HydraDB combines a **Git-styled bitemporal ledger**, **CSR/CSC Compressed Adjacency Matrices**, and **HNSW vector attributes**.

Below is the technical gold standard, failure mode analysis, and 9-day execution strategy across all 6 core foundational pillars.

---

# Pillar 1: Temporal & Bitemporal Knowledge Substrate

### 1.1 Technical Deep Dive & Mechanics
Knowledge in an enterprise is non-static and dual-dimensional. Modeling history requires distinguishing between reality time and system ingestion time:
* **Valid Time ($T_{valid}$):** The real-world interval $[V_{start}, V_{end})$ during which a fact was true in the physical/business world (e.g., "Arjun was PM for Project Acme from Jan 15 to Jul 25").
* **Transaction Time ($T_{tx}$):** The database system record interval $[T_{start}, T_{end})$ during which a statement was stored as active state in the ledger before being updated or invalidated (e.g., "The database recorded Bob as PM on Jul 26 at 09:00:00 UTC").

Bitemporal knowledge graphs prevent **destructive state overwrites** and allow point-in-time state reconstruction (`AS OF T_valid AT T_tx`).

### 1.2 Gold-Standard Architecture
```
                                BITEMPORAL EDGE MODEL
 +----------------------------------------------------------------------------------+
 | Edge: (:Person {id: 'soham'}) -[:OWNS]-> (:Project {id: 'acme'})                |
 +----------------------------------------------------------------------------------+
 |  Properties:                                                                     |
 |    - valid_from : 2026-01-15T00:00:00Z  | valid_to : 2026-07-25T14:30:00Z       |
 |    - tx_from    : 2026-01-15T08:12:00Z  | tx_to    : 2026-07-25T14:35:00Z       |
 |    - state      : SUPERSEDES           | predecessor_edge_id : 'edge_8491'      |
 +----------------------------------------------------------------------------------+
```
1. **Append-Only Immutable Ledger:** Updates never perform SQL/Graph `DELETE` or `UPDATE` in place. State changes append new node/edge versions while updating $T_{tx\_to}$ on superseded versions.
2. **2D Temporal Indexing:** Nodes and edges are indexed in a 2D spatial/interval index (such as an $R$-Tree or dual Interval B-Tree on $T_{valid} \times T_{tx}$).
3. **CSR/CSC Snapshotting with Delta Streams:** Baseline CSR adjacency matrices represent graph snapshots at fixed transaction epochs ($T_{tx\_epoch}$). Real-time updates accumulate in an append-only in-memory delta ring-buffer.
4. **Point-in-Time Query Engine:** Intercepts graph traversals with a temporal predicate filter:
   $$\text{Active}(E) \iff (E.V_{start} \le t_{valid} < E.V_{end}) \land (E.T_{start} \le t_{tx} < E.T_{end})$$

### 1.3 Common Failure Modes
* **The "Flashback Bug" (Retroactive Knowledge Leakage):** Querying historical state (`AS OF valid_time = Jan 2025`) using system timestamps from present day without pinning $T_{tx}$, causing future assertions to leak into past queries.
* **Temporal Interval Overlaps & Gaps:** Out-of-order log ingestion creating overlapping valid-time intervals for mutually exclusive functional states (e.g., two different team leads active on the exact same project on the exact same day).
* **CSR Index Rebuild Explosions:** Graph traversal engines attempting to re-compress the entire CSR/CSC matrix on every single incoming event rather than applying delta-vectors over baseline checkpoints.

### 1.4 Optimal 9-Day Hackathon Build Strategy
* **Minimal Bitemporal Schema:** Add 4 explicit fields to all edges: `valid_from` (ISO string), `valid_to` (ISO string / null), `tx_ingested_at` (ISO string), `is_current` (boolean).
* **State Transition Ingestion Function:** When ingesting a state change (e.g., project ownership transfer), execute an atomic mutation:
  1. Find active edge (`is_current == true AND valid_to == null`).
  2. Update active edge: `valid_to = event.timestamp`, `is_current = false`, `tx_to = now()`.
  3. Insert new edge: `valid_from = event.timestamp`, `valid_to = null`, `tx_from = now()`, `is_current = true`.
* **Point-in-Time Cypher/Python Interceptor:** Provide a helper wrapper `query_as_of(graph, valid_time, tx_time)` that automatically injects timestamp constraints into edge filtering loops.

---

# Pillar 2: Entity & Alias Resolution Engine

### 2.1 Technical Deep Dive & Mechanics
Enterprise data contains fragmented representations of the same real-world entity (`"Sam"`, `"Soham Ratnaparkhi"`, `"s-ratna"`, `"sam@company.com"`, `"Slack ID: U08192"`). Entity & Alias Resolution is the process of clustering these fragmented identifiers into canonical nodes without destroying underlying raw metadata.

### 2.2 Gold-Standard Architecture
```
 +----------------------------------------------------------------------------------+
 |                    5-STAGE CASCADING RESOLUTION PIPELINE                         |
 +----------------------------------------------------------------------------------+
 | Stage 1: Deterministic Blocking -> LSH / Exact Email / SSO ID Hash Lookup       |
 | Stage 2: Approximate Matching   -> RapidFuzz (Jaro-Winkler) + Embedding Cosine    |
 | Stage 3: Graph Co-occurrence   -> Louvain/Leiden Graph Clustering on Interaction   |
 | Stage 4: Agentic LLM Decision  -> Bounded Prompting for (0.65 <= Score < 0.85)   |
 | Stage 5: Active Learning HITL  -> Interactive Human-in-the-Loop Review Queue     |
 +----------------------------------------------------------------------------------+
```
1. **Non-Destructive `SAME_AS` Graph Topology:** Raw entity nodes from ingestion sources are preserved. They maintain directed `SAME_AS` edges to a centralized `CanonicalEntity` node. Merges and splits simply update `SAME_AS` edge pointers.
2. **Deterministic & Phonetic Blocking (Pass 1):** Partition candidate pairs into blocks using exact email domain matching, Double Metaphone phonetic hashes, and MinHash LSH to prevent $O(N^2)$ comparison explosion.
3. **Multi-Feature Pairwise Scoring (Pass 2 & 3):** Calculate a composite link score:
   $$Score = w_1 \cdot \text{StringSim} + w_2 \cdot \text{VectorSim} + w_3 \cdot \text{CoOccurrenceGraphWeight}$$
4. **Agentic LLM Disambiguation (Pass 4):** For borderline confidence scores ($0.65 \le Score < 0.85$), send context snippets to a structured LLM prompt returning `{match: boolean, confidence: float, reasoning: string}`.

### 2.3 Common Failure Modes
* **Identity Collapse (Cascading False-Positive Merges):** A single false match (e.g., merging two employees named "David Smith") merges their subgraphs, causing thousands of projects and tasks to collapse into one entity.
* **Destructive In-Place Merges:** Overwriting node properties directly into a single merged record, making un-merging impossible when new clarifying data arrives.
* **Combinatorial $O(N^2)$ Pairwise Blocking Bottlenecks:** Skipping candidate blocking and running similarity across 500,000 entities.

### 2.4 Optimal 9-Day Hackathon Build Strategy
* **3-Layer Cascading Linker:** Hash lookup $\rightarrow$ `RapidFuzz` string matching ($>88$) + Cosine embedding similarity $\rightarrow$ Co-occurrence edge weight calculation.
* **Virtual Canonical Nodes:** Create nodes with label `CanonicalPerson` and connect raw handles (`slack:sam`, `github:s-ratna`) via `SAME_AS` edges.
* **React HITL Drawer:** Build a simple sidebar component in the UI with a "Split Alias" / "Confirm Merge" toggle button.

---

# Pillar 3: Enterprise Ontology Construction

### 3.1 Technical Deep Dive & Mechanics
Enterprise schemas must balance structural predictability with domain flexibility. Rigid top-down ontologies (OWL/RDF) break when processing noisy unstructured text, while completely unconstrained schemas (free-form Property Graphs extracted by LLMs) devolve into predicate explosion.

### 3.2 Gold-Standard Architecture
```
                        HYBRID L3 ONTOLOGY ARCHITECTURE
 +----------------------------------------------------------------------------------+
 | Layer 1: Core Domain Schema (Fixed Property Graph Backbone)                       |
 |          Nodes: Person, System, Project, Issue, Decision, Customer               |
 |          Edges: OWNS, ASSIGNED_TO, DEPENDS_ON, SUPERSEDES, EVIDENCE_FOR          |
 +----------------------------------------------------------------------------------+
 | Layer 2: Flexible Dynamic Property Bags (Validated via Pydantic / JSON Schema)  |
 |          Node.metadata = { "cost_center": "ENG-402", "tech_stack": ["Rust"] }    |
 +----------------------------------------------------------------------------------+
 | Layer 3: Semantic Taxonomy & OWL Export Layer                                    |
 |          SKOS taxonomy mapping + SHACL shapes for formal verification            |
 +----------------------------------------------------------------------------------+
```
1. **Fixed L1 Backbone:** Standardized core enterprise node types (`Person`, `Project`, `System`, `Issue`, `Decision`, `Customer`) and edge predicates (`OWNS`, `ASSIGNED_TO`, `DEPENDS_ON`, `SUPERSEDES`, `EVIDENCE_FOR`, `PARTICIPATED_IN`).
2. **Schema-Constrained LLM Extraction:** Extraction prompts are bounded using structured outputs (`instructor` / Pydantic JSON Schema enforcement).
3. **Extensible L2 Property Bags:** Non-standard attributes are stored inside a strongly-typed `metadata` JSON object on nodes and edges.
4. **Auto-Aliasing Predicate Canonicalizer:** Free-text predicates (`"managed by"`, `"headed by"`) map to canonical edge types (`OWNS`).

### 3.3 Common Failure Modes
* **Predicate Sprawl ("2,000 Edge Types"):** Allowing LLMs to freely invent edge labels (`IS_CURRENTLY_WORKING_UPON`), rendering multi-hop graph traversals impossible.
* **OWL/RDF Reasoner Halting:** Deploying description-logic reasoners (HermiT, Pellet) where a single inconsistent axiom crashes the reasoner.
* **Property Graph Type Drift:** Storing inconsistent types in property keys (`budget` as integer vs string `"$50k USD"`).

### 3.4 Optimal 9-Day Hackathon Build Strategy
* **Strict Pydantic Core Ontology:** Define exactly 6 Node types and 8 Edge types in Python/TypeScript.
* **Structured Output Extraction:** Use `instructor` on all LLM extraction calls to guarantee zero unapproved node/edge labels.
* **Dictionary Predicate Normalizer:** Hardcoded synonym map (`{"led by": "OWNS", "assigned to": "ASSIGNED_TO"}`).

---

# Pillar 4: Contradiction & Truth Resolution Engine

### 4.1 Technical Deep Dive & Mechanics
Enterprise knowledge sources frequently state contradictory facts (Slack says "Arjun is PM", Linear says "Sarah is lead"). Contradiction resolution determines canonical truth while retaining historical evidence using a **Truth Maintenance System (TMS)**.

### 4.2 Gold-Standard Architecture
```
                         TRUTH RESOLUTION SCORING ENGINE
 +----------------------------------------------------------------------------------+
 |  Fact Score = Authority(Source) * Exp(-lambda * Delta_T) * ExtractionConfidence  |
 +----------------------------------------------------------------------------------+
 |  Source Authority Hierarchy:                                                     |
 |    1. Linear / Jira (0.95)   -> System of record for task assignments          |
 |    2. GitHub PRs (0.90)     -> System of record for code ownership             |
 |    3. Fireflies (0.85)      -> Verbal executive decisions in meetings          |
 |    4. Slack Channels (0.65) -> Informal operational announcements             |
 |    5. Email / DM (0.50)     -> Private / low-confidence claims                 |
 +----------------------------------------------------------------------------------+
```
1. **Multi-Factor Truth Scoring:** Calculate dynamic authority scores:
   $$S(F) = w_{\text{source}} \cdot e^{-\lambda(t_{\text{now}} - t_{\text{valid}})} \cdot C_{\text{extraction}}$$
2. **Belief Revision & State Invalidation:**
   * If $S(F_{\text{new}}) > S(F_{\text{active}})$: Mark $F_{\text{active}}$ as `SUPERSEDED` (`valid_to = now()`), create a `SUPERSEDES` edge from $F_{\text{new}} \to F_{\text{active}}$, and promote $F_{\text{new}}$ to active canonical state.
   * If $S(F_{\text{new}}) \le S(F_{\text{active}})$: Retain $F_{\text{active}}$ as canonical state and record $F_{\text{new}}$ with state `CONTRADICTION_CLAIM`.
3. **Explicit Graph Contradiction Index:** Insert bidirectional `CONTRADICTS` graph edges between conflicting fact nodes.

---

# Pillar 5: Graph Provenance & Lineage Substrate

### 5.1 Technical Deep Dive & Mechanics
Every synthesized answer generated by an enterprise AI must answer: **"Why is this true?"** Graph provenance maintains auditable chains of evidence connecting synthesized facts back through entity resolutions to raw source artifacts.

### 5.2 Gold-Standard Architecture
```
                           W3C PROV-O LINEAGE DAG
 +----------------------------------------------------------------------------------+
 |  [Raw Slack Message] ---> (:Document {id: 'doc_91'})                             |
 |                                    |                                             |
 |                             [:EVIDENCE_FOR]                                      |
 |                                    v                                             |
 |  [Extracted Triple]  ---> (:Edge {type: 'OWNS', id: 'edge_44'})                  |
 |                                    |                                             |
 |                             [:DERIVED_FROM]                                      |
 |                                    v                                             |
 |  [Canonical Fact]    ---> (:CanonicalEdge {owner: 'Sarah Chen'})                 |
 +----------------------------------------------------------------------------------+
```
1. **W3C PROV-O Model Compliance:** Graph edges store provenance attributes linking synthesized entities/relations back to `Entity` (Source Document), `Activity` (Extraction Job Run ID), and `Agent` (LLM Model Version).
2. **Deterministic Subgraph Citation Retrieval:** Query engine extracts underlying `EVIDENCE_FOR` subgraph paths alongside graph nodes.
3. **Sub-200ms Lineage Trace Traversal:** HydraDB's CSR/CSC layout resolves 4-hop evidence chains in under 5ms.

---

# Pillar 6: Enterprise Permissions & RBAC/ABAC Graph Authorization

### 6.1 Technical Deep Dive & Mechanics
Permissions must be enforced natively during graph traversal (**ReBAC - Relationship-Based Access Control** / **ABAC**) rather than post-filtering query results.

### 6.2 Gold-Standard Architecture
```
                    NATIVE PUSH-DOWN GRAPH AUTHORIZATION
 +----------------------------------------------------------------------------------+
 |  User Request Context: { user_id: 'alice', groups: ['eng', 'acme_team'] }        |
 +----------------------------------------------------------------------------------+
 |  Graph Traversal Loop (CSR Matrix Level):                                        |
 |    Hop 1: (:Person {id: 'alice'}) -[:MEMBER_OF]-> (:Team {id: 'eng'})  [ALLOWED]   |
 |    Hop 2: (:Team {id: 'eng'}) -[:HAS_ACCESS]-> (:Project {id: 'acme'}) [ALLOWED]   |
 |    Hop 3: (:Project) -[:HAS_SECRET]-> (:Secret {id: 'sec_9'})          [PRUNED]    |
 |           Edge.access_groups = ['execs'] -> Access Denied -> Path Terminated    |
 +----------------------------------------------------------------------------------+
```
1. **Zanzibar-Style ReBAC Model:** Permissions are modeled as graph edges (`User -[:MEMBER_OF]-> Team -[:CAN_VIEW]-> Project`).
2. **Push-Down Traversal Pruning:** Permission checks evaluate at the adjacency matrix traversal level (CSR lookup). Unauthorized branches are **pruned immediately**.
3. **ABAC Tagging:** Nodes and edges store security classification tags (`access_groups: ["engineering", "execs"]`).

---

## Consolidated Architecture Matrix for 9-Day Hackathon

| Pillar | Architectural Pattern | Fail-Safe Mechanism | 9-Day Hackathon Build Strategy |
| :--- | :--- | :--- | :--- |
| **1. Temporal Knowledge** | Append-only ledger ($T_{valid}, T_{tx}$), CSR Snapshot + Delta Buffer | Bitemporal filter predicate in query interceptor | Edge attributes (`valid_from`, `valid_to`, `is_current`) + Python `as_of()` wrapper |
| **2. Alias Resolution** | 5-stage cascade (Hash $\to$ String $\to$ Co-occurrence $\to$ LLM $\to$ HITL) | Virtual `SAME_AS` graph topology (non-destructive) | 3-Layer Waterfall + LLM 1-shot agent + React HITL drawer |
| **3. Enterprise Ontology** | Hybrid L3 (Fixed L1 backbone + Extensible L2 Property Bags) | Schema-constrained LLM output (Pydantic/`instructor`) | 6 Node / 8 Edge Pydantic Schema + Predicate synonym normalizer |
| **4. Contradiction Resolution**| TMS engine + Source authority hierarchy + Exponential decay | Invalidation via `SUPERSEDES` + `CONTRADICTS` index | Authority JSON dict + deterministic scoring + UI "Truth Alert" badge |
| **5. Graph Provenance** | W3C PROV-O lineage DAG (`EVIDENCE_FOR` edges) | Multi-hop citation injection into LLM prompts | Edge provenance metadata (`doc_id`, `url`, `snippet`) + Visual Lineage sidebar |
| **6. Enterprise ACLs** | Zanzibar ReBAC + Push-down edge pruning | Early traversal pruning at adjacency matrix layer | Edge `access_groups` array + push-down filtering + UI Persona Switcher |
