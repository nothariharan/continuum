# HydraDB: Vision, Core Architecture & Ecosystem Analysis

> **Document Version:** 1.0  
> **Target Event:** Hack Hydra Open Source Hackathon (Aug 12–20, 2026)  
> **Official Website:** [hydradb.com](https://hydradb.com) | **Twitter/X:** [@hydra_db](https://x.com/hydra_db) | **GitHub:** [`usecortex`](https://github.com/usecortex)

---

## 1. Executive Summary & Company Profile

**HydraDB** is a graph-native context infrastructure and composite memory substrate engineered specifically for AI agents, LLM applications, and complex enterprise knowledge networks. 

Unlike traditional vector databases that operate strictly on high-dimensional semantic similarity, HydraDB models data as an evolving, versioned knowledge graph. It allows AI systems to maintain long-term state, perform deterministic multi-hop reasoning, and preserve chronological audit trails across sessions.

### Key Company Metrics & Information
* **Founder & CEO:** Nishkarsh Srivastava (Entrepreneur & AI developer, previously founded *Findr*).
* **Core Technical Team:** 
  * **Harnoor Singh** (*DevRel Engineer*, known online as *"Singh in USA"* `@iharnoor` / 1M+ YouTube subscribers, ex-Microsoft Security).
  * **Abhirup Vijay Gunakar** (*Member of Technical Staff - MTS*).
  * **Akash Bhat** (*Technical Collaborator & Event Host*).
* **Funding:** ~$6.5M – $7M Seed Round led by **Sky9 Capital**.
* **Angel Investors:** 
  * **Jeff Dean** (Chief Scientist at Google DeepMind / Google Senior Fellow)
  * **Nikesh Arora** (CEO, Palo Alto Networks)
  * **Gokul Rajaram** (Board Member & angel investor)
  * **Wade Foster** (Co-founder & CEO, Zapier)

---

## 2. The Core Problem HydraDB Solves: "Beyond Flat Vectors"

Standard Retrieval-Augmented Generation (RAG) relies on dense vector embeddings (e.g., Pinecone, Qdrant, Chroma). While vector search is effective for finding semantically similar text, it fails catastrophically in production agent workflows due to three systemic vulnerabilities:

```
+-------------------------------------------------------------------------------+
|                       Vector Database Vulnerabilities                         |
+-------------------------------------------------------------------------------+
| 1. "Context Rot" & Blind Similarity:                                         |
|    Vector search finds text chunks with similar words but lacks structural     |
|    understanding of ownership, causality, or entity relationships.            |
|                                                                               |
| 2. Destructive State Overwrites:                                             |
|    Standard databases mutate state destructively. They cannot perform          |
|    point-in-time temporal queries (e.g., "What was true on May 10th?").        |
|                                                                               |
| 3. Multi-Hop Blind Spots:                                                    |
|    Multi-step relational queries (Slack -> Ticket -> PR -> Code Service)      |
|    require graph traversals that vector search physically cannot execute.     |
+-------------------------------------------------------------------------------+
```

---

## 3. The Triad Storage Architecture

HydraDB achieves sub-200ms recall latency while being **10x cheaper** than traditional memory-heavy graph databases by building directly on **Object Storage (S3 / Parquet)** using a three-part engine architecture.

```
+-------------------------------------------------------------------------------+
|                                HydraDB Engine                                 |
+-------------------------------------------------------------------------------+
|  1. Hot Tier (RAM)          : Low-latency active working context              |
|  2. Warm Tier (NVMe SSD)    : Compressed Sparse Row (CSR/CSC) Graph Adjacency |
|  3. Cold Tier (S3/Parquet)  : Scalable temporal graph ledger & archival       |
+-------------------------------------------------------------------------------+
|  • Git-Styled Bitemporal Graph: Versioned ledger (T_valid, T_tx)               |
|  • Native Vector Substrate (HNSW): Semantic search over entity attributes     |
|  • B-Tree Attribute Indexes   : Rapid property filtering & metadata lookup    |
+-------------------------------------------------------------------------------+
```

### Architectural Component Breakdown

1. **Git-Styled Bitemporal Graph:**
   Every entity, relationship edge, and property mutation is appended to a versioned ledger. Every graph element carries dual temporal attributes:
   * **Valid Time ($T_{valid}$):** The real-world timeframe during which the fact was true.
   * **Transaction Time ($T_{tx}$):** The system timestamp when the fact was ingested.
   * *Benefit:* Enables non-destructive history and `AS OF TIME T` point-in-time snapshot queries.

2. **Index-Free Adjacency via CSR/CSC Memory Layouts:**
   Instead of executing expensive SQL join operations, HydraDB stores graph adjacency matrices in Compressed Sparse Row (CSR) and Compressed Sparse Column (CSC) contiguous memory arrays.
   * *Benefit:* Enables sub-millisecond graph traversals per hop ($O(1)$ edge traversal time).

3. **Object Storage First Architecture:**
   Warm and cold graph segments are compressed into Parquet-style columnar files and offloaded to object storage (AWS S3, Cloudflare R2, GCP Cloud Storage).
   * *Benefit:* Reduces RAM footprints by 90%, enabling multi-million node graphs at dramatically lower infrastructure costs.

---

## 4. Current GitHub Ecosystem (`usecortex` Organization)

HydraDB maintains a suite of developer integrations under its GitHub organization [`usecortex`](https://github.com/usecortex):

* **`usecortex/hydradb-mcp`:** Model Context Protocol (MCP) server enabling persistent memory operations (`store`, `recall`, `search`) for AI coding tools like Claude and Cursor.
* **`usecortex/hydradb-cli`:** Command-line tool for managing memories, viewing graph structures, and running terminal ingestion.
* **`usecortex/hydradb-claude-code`:** Official extension for Claude Code providing cross-session memory and workspace documentation synchronization.
* **`usecortex/openclaw-hydradb`:** Plugin for OpenClaw providing automated conversation capture and memory graph extraction.

---

## 5. Summary for Hackathon Builders

When building for **Hack Hydra**, your project should directly demonstrate why **flat vector search fails** and how **HydraDB's graph structure + temporal versioning** solves a problem that would otherwise be impossible or prohibitively expensive.
