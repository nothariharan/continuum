# Curated Ecosystem & Baselines: What to Build Off Of vs. What to Beat

> **Document Version:** 1.0  
> **Purpose:** Detailed curation of pre-existing open-source libraries, APIs, datasets, and baseline frameworks across all hackathon tracks. Identifies open-source building blocks to accelerate 9-day development and baseline systems to outperform.

---

## 1. Curation Overview Matrix

```
+-----------------------------------------------------------------------------------+
| Track         | What We BUILD OFF OF (Ingestion & APIs) | What We NEED TO BEAT    |
+---------------+-----------------------------------------+-------------------------+
| Track 02A     | • OSV.dev REST API & osv-detector       | • npm audit / Snyk      |
| (Supply Chain)| • npm Registry CouchDB Feed / JSON API  | • Dependabot            |
|               | • GitHub Advisory Database (GHSA)       | • Vector-only RAG       |
|               | • @xyflow/react / vis-network UI        |                         |
+---------------+-----------------------------------------+-------------------------+
| Track 03      | • Mem0 (mem0ai/mem0) schemas & SDK      | • Native Mem0 / Zep     |
| (Memory)      | • LongMemEval & LongMemEval-V2 datasets | • Destructive memory    |
|               | • BEAM benchmark datasets               | • Vector-only memory    |
+---------------+-----------------------------------------+-------------------------+
| Track 01      | • Onyx (EnterpriseRAG-Bench) engine     | • Danswer default RAG   |
| (Enterprise)  | • Salesforce HERB dataset (HuggingFace) | • Naive semantic search |
|               | • dedupe / rapidfuzz Python libraries   |                         |
+---------------+-----------------------------------------+-------------------------+
| Track 02B     | • Tree-sitter AST multi-lang parsers    | • Cursor / Claude Code  |
| (Code Graphs) | • SWE-bench / SWE-bench Lite            |   vector-only similarity|
+-----------------------------------------------------------------------------------+
```

---

## 2. Track 2A Curation (Supply Chain Blast Radius) — Our Winning Project

### What We Can BUILD OFF OF:
1. **OSV.dev (Open Source Vulnerability Specification & API):**
   * **API Endpoint:** `https://api.osv.dev/v1/query`
   * **Open-Source Scanner:** [`G-Rath/osv-detector`](https://github.com/G-Rath/osv-detector) — standardized Go/Python lockfile vulnerability parser.
   * **Utility:** Provides structured JSON advisories matching package versions to affected SemVer ranges (`[1.0.0, 5.28.1)`).

2. **npm Ecosystem Metadata APIs:**
   * **Registry API:** `https://registry.npmjs.org/<package-name>`
   * **Public Data dumps:** `all-the-package-names` (npm registry index).
   * **Utility:** Provides version release histories, SemVer dependency declarations (`package.json`), and maintainer account metadata (`owners`).

3. **GitHub Advisory Database (GHSA):**
   * **API Endpoint:** GitHub GraphQL API (`securityAdvisories`).
   * **Utility:** Ground truth for CVE records, attack vectors, severity scores, and fix commits.

4. **Frontend & Graph Visualization:**
   * **React Flow (`@xyflow/react`):** Interactive node-edge canvas for rendering live dependency graphs.
   * **D3 Force / Vis Network:** High-performance canvas visualizers for multi-hop blast radius trees.

### What We Need to BEAT:
1. **Standard `npm audit` / Snyk / Dependabot:**
   * *Their Flaw:* They inspect **single repositories locally** in isolation. They cannot perform a **transitive reverse dependency closure** across a multi-repo corporate ecosystem graph in real time.
2. **Flat Vector Database Security Searches:**
   * *Their Flaw:* Vector search over security advisories can explain what a CVE means semantically, but **cannot compute graph path traversals**.

---

## 3. Track 03 Curation (Agent Memory & Context Retrieval)

### What We Can BUILD OFF OF:
1. **Mem0 (`mem0ai/mem0`):**
   * Universal open-source memory layer. Provides foundational patterns for memory extraction prompts, vector storage interfaces, and MCP servers.
2. **Open-Source Benchmark Datasets:**
   * **LongMemEval & LongMemEval-V2:** `github.com/xiaowu0162/LongMemEval`
   * **BEAM:** `github.com/mohammadtavakoli78/BEAM`

### What We Need to BEAT:
1. **Default Mem0 & Zep Implementations:**
   * *Their Flaw:* Destructive fact mutations (updating a fact overwrites the past state, causing temporal confusion).
   * *Their Flaw:* High failure rates on **abstention** (hallucinating answers when queried about missing facts).

---

## 4. Track 01 Curation (Enterprise Context & Ontology)

### What We Can BUILD OFF OF:
1. **Onyx Engine (`onyx-dot-app/EnterpriseRAG-Bench`):**
   * Formerly Danswer, an open-source enterprise search engine with multi-connector pipelines for Slack, Jira, GitHub, Gmail, and Google Drive.
2. **Salesforce HERB Dataset:**
   * Available on HuggingFace (`Salesforce/HERB`), containing 39,190 enterprise artifacts and multi-hop queries.
3. **Record Linkage Libraries:**
   * Python `dedupe` library and `rapidfuzz` for fuzzy entity name matching.

### What We Need to BEAT:
1. **Standard Enterprise Search (Naive Dense Vector RAG):**
   * *Their Flaw:* Fails to resolve entity aliases (`@soham` vs `Sam` vs `S. Ratnaparkhi`) and cannot resolve contradictory statements across platforms.

---

## 5. Track 2B Curation (Code Graphs for IDE Assistants)

### What We Can BUILD OFF OF:
1. **Tree-sitter Parsers:**
   * Open-source multi-language AST parser used by GitHub, Neovim, and VS Code.
2. **SWE-bench Framework:**
   * Official evaluation framework for software engineering agents (`swebench/SWE-bench`).

### What We Need to BEAT:
1. **Cursor / Claude Code Vector Similarity Baselines:**
   * *Their Flaw:* Retrieving code chunks solely by embedding similarity misses call graph chains, interface definitions, and test mappings across files.
