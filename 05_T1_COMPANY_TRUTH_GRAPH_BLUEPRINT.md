# Strategic & Technical Blueprint: Company Truth Graph (Track 01)

> **Project Name:** `Company Truth Graph` (or `HydraBrain`)  
> **Target Track:** Track 01 — Enterprise Context + Ontology  
> **Target Award:** Grand Champion ($5,000) & Best Use of HydraDB ($500)  
> **Target Event:** Hack Hydra Hackathon (Aug 12–20, 2026)

---

## 1. Executive Summary & Strategic Positioning

### The Thesis
Enterprise AI applications do not fail because LLMs lack general intelligence. They fail because corporate knowledge is fractured across siloed software systems (Slack, Gmail, GitHub, Jira, Linear, HubSpot, Confluence, Drive, Fireflies) and filled with **aliases, outdated information, contradictory statements, and lost history**.

Traditional RAG systems treat company knowledge as a static pile of unstructured text documents. When queried, vector search returns fragmented chunks of text with conflicting statements, leaving the LLM to guess what is currently true.

**Company Truth Graph** turns Track 01 into **the operating system for enterprise truth**. Instead of document retrieval, it uses **HydraDB’s Git-styled bitemporal knowledge graph** to reconstruct the canonical, real-time organizational state of a company across 9 business tools.

```
+-----------------------------------------------------------------------------------+
|                        Flat RAG vs. Company Truth Graph                          |
+-----------------------------------------------------------------------------------+
| Flat Enterprise RAG:                                                              |
|   Query: "Who owns the Acme integration?"                                         |
|   Result: 14 text chunks from Slack, Jira, Gmail (3 say Arjun, 4 say Sarah).      |
|   Outcome: LLM hallucinates or delivers uncertain, conflicting answers.           |
|                                                                                   |
| Company Truth Graph (HydraDB Engine):                                             |
|   Query: "Who owns the Acme integration?"                                         |
|   Result: Current Owner: Sarah Chen (94% confidence).                             |
|           State Transition: Arjun Mehta (Jan 1 - Jul 25) -> Sarah Chen (Jul 25+). |
|           Provenance: Resolved across Linear #ACME-481, GitHub PR #1842, & Slack.  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Competitive Alignment: Why Track 01 & Why This Vision?

1. **Direct Alignment with HydraDB’s Company Mission:**
   HydraDB’s public positioning centers on structured context graphs, bitemporal versioning, agent memory, and company brains. Track 01 directly tackles the enterprise TAM that HydraDB is built to power.

2. **Differentiating from Generic Track 01 Submissions:**
   Most competitors will build "Document RAG + Neo4j + Chat UI". By framing the product as **State Reconstruction & Provenance**, we stand out with an ambitious, production-grade intelligence engine.

3. **Defensible Moat:**
   The moat is not finding documents; it is **resolving entity identity**, **reconciling temporal contradictions**, **generating multi-hop graph provenance**, and **simulating organizational dependencies**.

---

## 3. Core Product Capabilities & Demo Pillars

### Feature 1: Multi-System Alias & Entity Resolution Engine
Resolves disjointed handles (`Sam`, `@soham`, `S. Ratnaparkhi`, `sam@company.com`) into a single canonical entity node (`entity:person:soham_ratnaparkhi`) across all 9 data sources using exact identifier matching, string distance, and co-occurrence graph clustering.

### Feature 2: Temporal State & Ownership Ledger
Tracks ownership, team assignments, project status, and customer decisions over time ($T_{valid}, T_{tx}$). Provides instant historical timelines (`AS OF TIME T`) showing how truth evolved.

### Feature 3: Automated Contradiction Resolution
Detects conflicting statements across platforms (e.g., Slack says "Arjun is PM", Linear says "Sarah is lead"). Uses a confidence and temporal authority hierarchy to establish current canonical truth while logging the contradiction.

### Feature 4: Traceable Graph Provenance ("Why is this true?")
Every answer is backed by an auditable, interactive multi-hop graph path showing the exact chain of evidence from raw events to resolved state.

### Feature 5: Organizational Impact & Dependency Simulation ("What Breaks?")
Traverses graph edges outward from any entity to simulate organizational risk. (e.g., "If Sarah leaves, 7 projects, 3 production microservices, and 2 customer accounts are impacted").

---

## 4. Architecture & Graph Schema

```
   (Person: canonical_id) ---[:OWNS {valid_from, valid_to}]---> (Project)
            |                                                      |
     [:PARTICIPATED_IN]                                    [:HAS_ISSUE]
            v                                                      v
     (MeetingTranscript)                                        (Issue)
            |                                                      |
            +---[:DECIDED]---> (Decision) <---[:REFERENCES]--------+
                                   |
                         [:AFFECTS_CUSTOMER]
                                   v
                              (Customer)
```

### Node Types
* `Person`: Canonical employee entity with resolved aliases (`handles`, `emails`, `names`).
* `Project` / `System`: Technical or operational initiatives.
* `Customer` / `Account`: External organizations and contracts.
* `Issue` / `PR`: Jira/Linear tickets and GitHub pull requests.
* `Decision`: Explicit agreements made in meetings, Slack, or emails.
* `Document` / `Message`: Source evidence artifacts.

### Key Relationship Edges
* `OWNS` / `ASSIGNED_TO`: Substrate for team & task responsibility (`valid_from`, `valid_to`, `confidence`).
* `DEPENDS_ON`: Inter-project and service dependencies.
* `SUPERSEDES`: Edge connecting updated decisions or state changes over time.
* `EVIDENCE_FOR`: Traceability edge from raw document node to resolved relationship.

---

## 5. Technical Implementation Pipeline

```
  +-------------------+      +-------------------------+      +--------------------------+
  | Ingestion Layer   | ---> | Entity & Alias Resolver | ---> | Temporal HydraDB Ledger |
  | (500k docs / 9    |      | (Deterministic + ML     |      | (Bitemporal Edges +      |
  | connectors)       |      | Graph Clustering)       |      | CSR/CSC Traversal)       |
  +-------------------+      +-------------------------+      +--------------------------+
                                                                            |
  +-------------------+      +-------------------------+                    v
  | Interactive UI &  | <--- | Multi-Hop Reasoning &   | <------------------+
  | Simulation Engine |      | Provenance Generator    |
  +-------------------+      +-------------------------+
```

### Stage 1: Ingestion & Parsing
* Ingest synthetic dataset from **EnterpriseRAG-Bench** / **Salesforce HERB**.
* Standardize schemas across Slack, Gmail, Linear, Drive, HubSpot, Fireflies, GitHub, Jira, Confluence into unified JSON objects.

### Stage 2: Entity & Alias Resolution (The Core Engine)
* **Layer 1 (Exact):** Unique IDs, email addresses, exact social handles.
* **Layer 2 (Fuzzy):** String similarity (`RapidFuzz`, Jaro-Winkler) over names and titles.
* **Layer 3 (Structural):** Co-occurrence graph clustering (Entities that co-attend the same Fireflies meetings, work on the same repos, and share channels belong to the same canonical node).

### Stage 3: Temporal Graph Ingestion (HydraDB)
* Create bitemporal graph edges in HydraDB with real-world timestamp ($T_{valid}$) and transaction timestamp ($T_{tx}$).
* Store entity vectors in HydraDB’s HNSW substrate for fast property lookups.

### Stage 4: Contradiction & Provenance Engine
* Run conflict detection queries on newly ingested facts.
* Execute multi-hop path traversals using HydraDB’s CSR/CSC graph adjacency.

---

## 6. Evaluation Framework (Benchmark vs. Product)

1. **Evaluation Layer (Benchmark Mode):**
   * Run against **EnterpriseRAG-Bench** (500 questions) and **Salesforce HERB**.
   * Measure: Multi-hop retrieval precision/recall, entity resolution accuracy, contradiction handling, abstention rate ("not in data" queries), and sub-200ms latency.

2. **Product Layer (Demo Mode):**
   * Production web dashboard rendering resolved state, historical evolution timeline, visual graph provenance, and dependency simulation canvas.

---

## 7. 9-Day Development Sprint Plan

* **Days 1–2:** Ingestion of EnterpriseRAG-Bench dataset + Entity Extraction & Alias Linker pipeline.
* **Days 3–4:** HydraDB Temporal Graph Ledger setup + Bitemporal edge invalidation & contradiction resolver.
* **Days 5–6:** Multi-hop reasoning engine + Graph provenance path generator + Organizational simulation logic.
* **Days 7–8:** Web UI (React Flow / D3 graph canvas) + Benchmark evaluation harness runs.
* **Day 9:** Documentation, README polish, and 3-Minute Video Recording.

---

## 8. Summary of Competitive Advantage

```
+----------------------------------------------------------------------------------+
| Without HydraDB : Vector search returns 15 conflicting text chunks.               |
| With HydraDB    : Reconstructs exact temporal state, resolves identity, proves    |
|                   provenance, and predicts organizational impact.                 |
+----------------------------------------------------------------------------------+
```
