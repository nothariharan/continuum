# Continuum: Empirical Failure Taxonomy & Production User Pain Analysis

> **Document Version:** 1.0  
> **Project:** `Continuum` (Enterprise Bitemporal Truth Engine)  
> **Source Material:** Agent Group 4 & 5 Community Complaint Stream (Hacker News, Reddit, GitHub Issues)  

---

## 1. Executive Summary

Enterprise search and RAG tools promise a unified knowledge layer across tools like Slack, Jira, Confluence, Google Drive, and GitHub. However, production deployments across enterprise environments reveal systemic architectural failures.

Rather than simple LLM generation errors, primary points of failure stem from **data plumbing, identity resolution, temporal degradation, and permission misalignment**. When AI engines interact with legacy enterprise data, they frequently act as **"permission auditors" exposing neglected security controls**, produce fluent hallucinations backed by obsolete 3-year-old documentation, or silently average contradictory facts across communication channels.

---

## 2. Tool-by-Tool Empirical Failure Breakdown

### 1. Glean
* **Primary Mechanics:** Centralized connectors with vector indexing, semantic search, and enterprise ACL syncing.
* **Empirical Complaints & Pain Points:**
  * **Vector vs. Graph Limitation:** Backend relies heavily on vector similarity search rather than a true dynamic knowledge graph, causing hallucinations on multi-step relationship queries (e.g., matching customer edge cases to specific code repos and Jira owners).
  * **High Entry Cost & Contract Friction:** Sales-driven pricing starting at $18–$30+/user/month with high annual minimums.
  * **Human-in-the-Loop Scoping Gap:** Lack of explicit context scoping (users cannot easily say *"Search only these 3 specific Google Docs and this 1 Slack channel"*).
  * **ACL Sync Latency:** Permission sync delays allow recently revoked document permissions to return content snippets in search previews.

### 2. Microsoft 365 Copilot
* **Primary Mechanics:** Built on Microsoft Graph API, utilizing tenant-level indices and native M365 permissions.
* **Empirical Complaints & Pain Points:**
  * **The "Permissions Auditor" Effect:** Copilot trivially surfaces decades of hidden internal "oversharing" (documents in loosely permissioned SharePoint sites containing salaries, layoff drafts, performance reviews).
  * **Draft & Sent Mail Summarization Bugs:** Copilot summarized confidential, un-sent draft emails or restricted "Sent" folder threads into general user summaries, ignoring Data Loss Prevention (DLP) flags.
  * **Hallucination of Stale Enterprise Data:** Prioritizes high-frequency draft files or older SharePoint sites over updated canonical documents due to basic semantic similarity scoring that ignores timestamps.
  * **Commercial Sentiment:** Criticized on Hacker News as an expensive commercial failure ($30/user/mo addon) due to high latency and poor transparency when retrieval fails.

### 3. Notion AI
* **Primary Mechanics:** Embedded vector RAG querying the Notion workspace page database.
* **Empirical Complaints & Pain Points:**
  * **Single-Workspace Siloing:** Completely blind to context outside Notion (Slack threads, GitHub PRs).
  * **Active vs. Archived Page Noise:** Q&A routinely retrieves outdated specs from archived folders, presenting 2022 architecture plans as current 2026 specs.
  * **Formatting Block Destruction:** Accidental deletion of complex block types (database views, inline code blocks, synced blocks) when editing pages.

### 4. Slack AI
* **Primary Mechanics:** Search and summarization pipeline operating over channel message history and thread blocks.
* **Empirical Complaints & Pain Points:**
  * **Noise-to-Signal Chunking Bias:** Informal chat generates massive volumes of short text chunks; Slack AI frequently retrieves preliminary brainstorming comments or jokes as "consensus decisions."
  * **Ephemeral Context Decay:** Fails to resolve transient chat handles or shorthand ("Let me check with Dave") into persistent canonical entities.
  * **Hallucination of Consensus:** Takes the final message in a thread as authoritative even if it was a rejected proposal.

### 5. Atlassian Rovo
* **Primary Mechanics:** Atlassian Team Central context engine paired with RAG over Jira keys and Confluence nodes.
* **Empirical Complaints & Pain Points:**
  * **Forced Rollout & Admin Friction:** Sysadmin frustration over forced, opt-out-heavy admin popups in Atlassian Cloud.
  * **Shallow Retrieval:** Struggles to bridge the semantic gap between a high-level Confluence spec and technical Jira issue comments.
  * **Graveyard Effect:** Summaries pull in abandoned "Draft" specs or deprecated runbooks.

### 6. Hebbia (Matrix RAG)
* **Primary Mechanics:** "Matrix" extraction engine ingesting document sets (100k+ pages) into structured grid views using parallel LLM extraction agents.
* **Empirical Complaints & Pain Points:**
  * **Explosive Token & API Costs:** High token throughput over thousands of SEC filings makes contract costs extremely high ($50k–$100k+ enterprise contracts).
  * **Non-Deterministic Grid Extraction:** Subtle prompt format variations or foundation model updates cause identical PDF contracts to populate differently across Matrix columns.
  * **Integration Gap:** Lack of real-time bi-directional sync with Microsoft Excel.

---

## 3. Deep-Dive Analysis of the 8 Core Failure Categories

```
+-----------------------------------------------------------------------------------+
|                        ENTERPRISE RAG FAILURE TAXONOMY                            |
+--------------------------+----------------------------------+---------------------+
| Category                 | Failure Mechanism                | Enterprise Impact   |
+--------------------------+----------------------------------+---------------------+
| 1. Stale Data & Halluc.  | Density bias over curated KBs    | Outdated execution  |
| 2. Entity Alias Res.     | Cross-silo identity decay        | Fractured context   |
| 3. Conflicting Facts     | Silent averaging / no referee    | Misinformation      |
| 4. Context Loss / Overw. | Lack of bi-temporal modeling     | History erased      |
| 5. ACL & Permission Leak | "Permissions auditor" effect     | Severe data breach  |
| 6. Poor Multi-Hop        | Single-pass vector breakdown     | Shallow retrieval   |
| 7. Provenance Deficit    | Hallucinated / dead citations    | Zero trust audit    |
| 8. Graph Cost & Brittle  | $33k indexing; schema drift      | Abandoned GraphRAG  |
+--------------------------+----------------------------------+---------------------+
```

### 1. Hallucinations and Out-of-Date / Stale Information
* **Mechanism:** Vector search is agnostic to document freshness or authoritativeness. High-volume chat channels dominate top-k results over official documentation.
* **Root Cause:** Absence of metadata-weighted temporal scoring and failure to apply tiered retrieval weighting.

### 2. Inability to Resolve Entity Aliases
* **Mechanism:** Organizations store identity across distinct platforms without a global entity key (`@jchen` in Slack vs `John Chen` in Gmail vs `jchen-dev` in GitHub). Vector embeddings treat these string variants as separate entities.
* **Root Cause:** Conflating raw text extraction with canonical entity resolution. Failure to maintain an identity graph linking cross-platform OAuth IDs to a unified employee node.

### 3. Inability to Reconcile Conflicting Facts Across Silos
* **Mechanism:** When RAG ingests data from multiple tools with contradictory claims (Slack vs Jira), LLMs either silently pick the first chunk or hallucinate a false blend.
* **Root Cause:** Lack of a "Referee Layer" or authority hierarchy in RAG pipelines.

### 4. Loss of Historical Context & State Overwriting
* **Mechanism:** Standard indexing overwrites vector embeddings when a file is edited. Without bi-temporal data modeling ($T_{valid}$ vs $T_{tx}$), systems cannot answer historical queries ("What was our EU policy in Q3 2023?").
* **Root Cause:** Ingestion pipelines lack versioned delta-indexing and bi-temporal graph nodes.

### 5. Permission Leaks and ACL Headaches
* **Mechanism:** Enterprise search platforms copy complex ACLs into vector stores. Permission sync lag or OAuth scope drift causes restricted vector content to appear in user search previews.
* **Root Cause:** Overly permissive legacy file permissions combined with vector filtering bugs and slow ACL cache revalidation.

### 6. Poor Multi-Hop Reasoning Across Tools
* **Mechanism:** Multi-hop queries require logical chains across tool boundaries (Query $\rightarrow$ Jira Key $\rightarrow$ GitHub PR $\rightarrow$ Author). Naive single-pass vector search fails when intermediate identifiers are required.
* **Root Cause:** Reliance on single-pass vector lookup instead of agentic tool use or pre-materialized cross-tool join indices.

### 7. Lack of Provenance & Un-Auditable Outputs
* **Mechanism:** LLMs synthesize text across retrieved chunks but lose direct mappings to source chunk IDs, hallucinating URL links or citing non-existent line numbers.
* **Root Cause:** Absence of deterministic post-generation citation validation.

### 8. High Indexing Costs & Brittle Ontology Maintenance in GraphRAG
* **Mechanism:** Eager LLM entity/relationship extraction over 500k documents costs $33,000+ in API tokens and requires full re-indexing when domain schemas evolve.
* **Root Cause:** Eager extraction using heavy LLMs instead of lightweight NLP pipelines + dynamic graph indexing ("Lazy GraphRAG").

---

## 4. Architectural Solutions Built into `Continuum`

1. **Pre-Materialized Identity Graphs:** Continuously maps cross-tool aliases (`@username`, email, GitHub ID, Jira key) to canonical UUIDs *before* vector ingestion.
2. **Bi-Temporal Metadata Encoding:** Tags every chunk with $T_{valid}$ (world event time) and $T_{tx}$ (system record time) to prevent state overwrites and enable time-travel queries (`AS OF TIME T`).
3. **Lazy GraphRAG / Hybrid Retrieval:** Combines spaCy/dependency parsing with vector search, reserving heavy LLM summarization for query time to drop indexing costs by 100x.
4. **Deterministic Citation Verification:** Enforces hard programmatic verification of citations against retrieved chunk metadata before output rendering.
5. **Conflict-Aware Referee Agent:** Implements Doyle-style TMS dependency tracking with explicit source authority weighting to flag discrepancies rather than synthesizing false consensus.
