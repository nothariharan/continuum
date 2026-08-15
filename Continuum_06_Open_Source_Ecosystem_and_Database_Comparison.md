# Continuum: Open-Source Ecosystem & Graph Database Comparison

> **Document Version:** 1.0  
> **Project:** `Continuum` (Enterprise Bitemporal Truth Engine)  
> **Source Material:** Agent Group 6, 7 & 8 Open Source & Graph Database Stream  

---

## Executive Summary

To achieve victory in **Hack Hydra**, our solution must legally leverage battle-tested open-source libraries, models, and frameworks while proving why **flat vector databases fail** and how **HydraDB's bitemporal CSR/CSC architecture** solves complex multi-hop and point-in-time context problems.

This document presents a curated inventory across **Hugging Face**, **GitHub Open-Source Repositories**, and **Graph Database Engines**.

---

## 1. Hugging Face Models & Pipelines

### A. Entity Resolution, Linking & Matching Models

| Model Name / Hub ID | Architecture & Technical Mechanism | Latency / Hardware | License | Commercial & Hackathon Legal Status | Recommended Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`sapienzanlp/relik-entity-linking-large`** | **Retriever-Reader Dual Encoder:** Uses dense retriever to select top-$k$ candidates from knowledge base, then reader aligns mentions in a single forward pass. | ~15–20ms on NVIDIA T4/A10G (~40x faster than LLMs) | **Apache 2.0** | **100% Safe** (Permissive) | Linking mention strings in raw text to canonical entity IDs (Wikidata or custom entity dictionary). |
| **`gliner-community/gliner-v2.5`** | **Bi-Encoder Token/Span Transformer:** Zero-shot NER model allowing dynamic entity type definitions without re-training. | ~30ms CPU / ~5ms GPU | **Apache 2.0** | **100% Safe** (Permissive) | Extracting custom entity types on the fly (e.g., `npm_package`, `cve_id`, `person_alias`, `commit_hash`). |
| **`facebook/blink`** | **Two-Stage Entity Linking:** Bi-encoder candidate retriever over dense Wikipedia embeddings + Cross-encoder reranker. | ~100–150ms per batch | **MIT** | **100% Safe** (Permissive) | Large-scale entity disambiguation against massive enterprise entity catalogs. |
| **`spacy` (`en_core_web_trf` + `EntityLinker`)** | **RoBERTa + Prior Probability KB:** Combines transformer embeddings with in-memory `KnowledgeBase` frequency counts. | Sub-5ms per doc | **MIT** | **100% Safe** (Permissive) | Rapid baseline entity extraction and canonical dictionary mapping in streaming pipelines. |

---

### B. Coreference Resolution & Reranking Models

| Model Name / Hub ID | Architecture & Technical Mechanism | Latency / Hardware | License | Key Function |
| :--- | :--- | :--- | :--- | :--- |
| **`fastcoref` (`shon-otmazgin/fastcoref`)** | **F-COREF Architecture:** Replaces $O(N^3)$ span pairwise comparisons with single-pass token representations built on DeBERTa. | ~10–15ms per 1,000 tokens | **MIT** | **50x faster than traditional neural coref.** Essential for resolving pronouns across multi-session conversations. |
| **`BAAI/bge-reranker-v2-m3`** | Multilingual Cross-Encoder Transformer. Computes deep cross-attention between query and candidate subgraph nodes. | ~15–30ms per batch on GPU | **MIT** | Reranking top-$k$ graph candidate paths retrieved from HydraDB vector queries. |
| **`cross-encoder/ms-marco-MiniLM-L-6-v2`** | 6-layer lightweight cross-encoder transformer. | **Sub-5ms on CPU** | **Apache 2.0** | Ideal for CPU-only lightweight local dev servers. |

---

## 2. GitHub Open-Source Repositories

### A. GraphRAG & Framework Repositories

| Repository | Stars | License | Architecture Overview | Production Readiness | Hackathon Fit & Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`microsoft/graphrag`** | ~34.5k+ | **MIT** | Hierarchical community detection (Leiden algorithm) + LLM summarization + Graph indexing. | Production-grade for offline batch indexing. | High cost/latency limitation ($33k+ in tokens). Reference for global summarization. |
| **`HKUDS/LightRAG`** | ~36.9k+ | **MIT** | Dual-level retrieval (low-level entity nodes + high-level community summaries) with integrated vector search. | High. Extremely active development. | **10x faster indexing** than Microsoft GraphRAG. Excellent baseline for `Continuum`. |
| **`OSU-NLP-Group/HippoRAG`** | ~4.2k+ | **MIT** | Personalized PageRank (PPR) over OpenIE subgraphs. | High. | **10x–30x faster multi-hop traversal** over HydraDB vector nodes. |

---

### B. Entity Resolution Frameworks

| Repository | Stars | License | Core Technology & Backend | Production Readiness | Best Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`moj-analytical-services/splink`** | ~2.3k+ | **MIT** | Probabilistic record linkage (Fellegi-Sunter model) using Expectation-Maximization (EM) on DuckDB. | **Enterprise Standard** | Resolving millions of entity pairs across enterprise systems. |
| **`dedupeio/dedupe`** | ~3.6k+ | **MIT** | Machine learning entity resolution using active learning and string distance metrics. | High. | Semi-supervised deduplication. |
| **`rapidfuzz/RapidFuzz`** | ~3.2k+ | **MIT** | C++ optimized string matching algorithms (Levenshtein, Damerau-Levenshtein, Jaro-Winkler). | **Ubiquitous Production Core.** | **Sub-microsecond string fuzzy matching** (100x faster than FuzzyWuzzy). |

---

## 3. Comprehensive Graph Database Comparison & HydraDB Architectural Contrast

### A. Deep Technical Matrix (8 Major Engines vs HydraDB)

| Database | Primary Architecture | Query Language | Bitemporal / Temporal Support | Native Vector Support | Index-Free Adjacency / Memory Layout | Traversal Latency (1-3 Hops) | License Model |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Neo4j** | Native Property Graph (Java) | Cypher / GQL | Property-level timestamps only (No native bitemporal ledger) | HNSW vector index in v5+ | Pointer chasing over JVM heap arrays | 1–5ms (High RAM footprint) | Dual (GPLv3 / Commercial) |
| **Memgraph** | In-Memory Graph (C++) | openCypher | Attribute timestamps | Basic vector search (MAGE) | Concurrent pointer structures in RAM | **<1ms** (Strictly RAM-bound) | BSL / Apache 2.0 |
| **Kuzu** | Embedded In-Process (C++) | Cypher (subset) | Attribute filtering; Arrow zero-copy | HNSW vector index extension | **Compressed Sparse Row (CSR)** | **<0.5ms** (Zero IPC overhead) | **MIT** |
| **TypeDB** | Polymorphic Object Graph (Rust/Java) | TypeQL | Rule-based temporal inferencing | Vector support in v3.0 | Type-indexed pointer arrays | 5–20ms (Rule overhead) | AGPLv3 / SSPL |
| **FalkorDB** | Matrix Linear Algebra (Redis/C) | Cypher | Property-level timestamps | Integrated Redis Vector Library | GraphBLAS Sparse Matrix operations | Sub-1ms (Matrix multiplication) | BSD-3 / SSPL |
| **ArangoDB** | Multi-Model (Doc + Graph) in C++ | AQL (Non-Cypher) | Document revision history | ArangoSearch vector index | Multi-model index lookups | 5–15ms (Multi-model overhead) | Apache 2.0 |
| **NebulaGraph** | Distributed Shared-Nothing (C++) | nGQL | Edge versioning via timestamp keys | Vector index plugin | Distributed partition keys | 5–20ms (Network hops) | Apache 2.0 |
| **RDF / SPARQL** | Triple Store (Subject-Predicate-Object) | SPARQL | OWL-Time ontology / Named graphs | Modern triplestore vector plugins | Triple index tables (GSPO / POSG) | 10–50ms (Join heavy) | Apache 2.0 / BSD |
| **HYDRADB** | **Triad Storage Engine (RAM / NVMe SSD / S3 Parquet)** | **Cypher / Native API** | **Native Git-Styled Bitemporal Ledger ($T_{valid}, T_{tx}$)** | **Native HNSW Vector Substrate** | **CSR & CSC Contiguous Memory Layouts** | **Sub-1ms (Sub-200ms end-to-end recall)** | **Open-Source Substrate** |

---

### B. Structural Contrast: Why HydraDB Superiorly Solves Agent Context

```
+---------------------------------------------------------------------------------------------------+
|                                  HydraDB Architectural Supremacy                                  |
+---------------------------------------------------------------------------------------------------+
| 1. Triad Storage Engine (Object-Storage First):                                                   |
|    • Traditional DBs (Neo4j, Memgraph): Hold full graph in expensive RAM.                         |
|    • HydraDB: Tiered memory — Hot (RAM) -> Warm (NVMe CSR/CSC) -> Cold (S3/Parquet).               |
|    • Benefit: 10x cheaper infrastructure cost while preserving sub-200ms recall latency.          |
|                                                                                                   |
| 2. Contiguous CSR/CSC Memory Layout:                                                              |
|    • Traditional DBs: Use pointer-chasing linked lists (cache misses across JVM/RAM).            |
|    • HydraDB: Stores graph adjacency in contiguous Compressed Sparse Row (CSR) and Column (CSC)   |
|      arrays in NVMe/RAM. Enables hardware SIMD vectorization and O(1) edge traversals.            |
|                                                                                                   |
| 3. Native Git-Styled Bitemporal Ledger:                                                            |
|    • Traditional DBs: Mutate records destructively (overwriting past state).                      |
|    • HydraDB: Every node/edge has dual timestamps:                                                 |
|      - Valid Time (T_valid): Real-world interval when fact was true.                              |
|      - Transaction Time (T_tx): Log timestamp when system recorded the fact.                      |
|    • Benefit: Native point-in-time state reconstruction ("AS OF TIME T") with non-destructive history.|
|                                                                                                   |
| 4. Native Vector Substrate:                                                                       |
|    • Traditional DBs: Glue separate vector plugins to graph nodes.                                |
|    • HydraDB: Integrates HNSW vector indexing directly into entity property memory blocks.        |
+---------------------------------------------------------------------------------------------------+
```
