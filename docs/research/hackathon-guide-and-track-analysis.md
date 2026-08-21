# Hack Hydra: Participant Guide & Track Breakdown

> **Document Version:** 1.0  
> **Source Material:** [Hack Hydra Participant Guide.pdf]((local source PDF))  
> **Hackathon Dates:** August 12–20, 2026 | **Submission Deadline:** August 20, 2026 at 11:59 PM PT  
> **Prize Pool:** $10,000 Total ($5k Grand Champion, $3k Runner-Up, $1.5k 3rd Place, $500 Best Use of HydraDB)

---

## 1. Hackathon Deadlines & Mandatory Deliverables

### Mandatory Checklist for Eligibility
Every submission **must** include three items submitted before **August 20 at 11:59 PM PT** through the official Google Form (`forms.gle/GrMYKxLj9zPQcqqc8`):

1. **Official Submission Form:**
   * Project name, short description, and track selection.
   * Description of problem addressed, what was built, and deployed project link (if applicable).
   * Detailed explanation of how HydraDB is used.
   * Tech stack, team member list, GitHub repo link, and 3-minute video link.

2. **Public GitHub Repository:**
   * Complete source code with an open-source license (MIT, Apache 2.0, BSD).
   * **Strict Rule:** No participant-authored commits before August 12, 2026. Reusing open-source libraries, frameworks, APIs, public datasets, and AI coding assistants is **100% allowed** (must be credited in README).
   * Clear README with setup/run instructions and an explanation of HydraDB's role.

3. **3-Minute Demo Video (Strictly Evaluated):**
   Must cover four elements in order:
   * **The Problem:** What real-world pain point are you solving?
   * **The Project:** What did you actually build?
   * **The Live Demo:** Show the working system in action executing real queries.
   * **HydraDB Integration:** Where is HydraDB used, and why does it matter?

---

## 2. Official Judging Criteria & Philosophy

Judges evaluate projects first within their track, and the top submission from each track advances to the final round. Placement is determined holistically across all finalists.

```
+-------------------------------------------------------------------------------+
|                           Official Judging Matrix                              |
+-------------------------------------------------------------------------------+
| 1. Technical Execution                    : Depth & robustness of code        |
| 2. Use of HydraDB & Graph-Native Methods  : Graph traversal vs vector search  |
| 3. Product Completeness & Usability       : Working end-to-end demo           |
| 4. Quality of Results                     : Precision, recall & accuracy      |
| 5. Originality                            : Novelty of approach & utility     |
+-------------------------------------------------------------------------------+
| GOLDEN ADVICE FROM JUDGES (Page 11):                                           |
| "We care about working, thoughtful products, not just benchmark scores...     |
|  Stop adding features before the deadline. Test what you already built.        |
|  Build small. Test early. Ship something real."                                |
+-------------------------------------------------------------------------------+
```

---

## 3. Exhaustive Track Breakdown

### Track 01: Enterprise Context + Ontology
* **Core Problem:** 500,000 documents across 9 business tools (*Slack, Gmail, Linear, Google Drive, HubSpot, Fireflies, GitHub, Jira, Confluence*).
* **Hard Part:** Entity resolution (recognizing `Sam` = `@soham` = `S. Ratnaparkhi`) and ontology alignment across conflicting statements.
* **Official Datasets:**
  * `github.com/onyx-dot-app/EnterpriseRAG-Bench` (Enterprise RAG Bench)
  * `huggingface.co/datasets/Salesforce/HERB` (Salesforce HERB Benchmark)
* **What Strong Work Shows:** Graph schema that survives noise; precise alias resolution; multi-hop answers with traceable graph paths; abstaining ("not in data") when answers are missing.

---

### Track 02: Repos, Dependencies + Code as Graphs

#### Option A: Supply Chain Blast Radius
* **Core Problem:** Supply chain attacks via npm/PyPI (e.g., TanStack compromise: 84 releases across 42 packages in 6 minutes). Speed is the defender's primary problem.
* **Key Queries to Answer:**
  * Which internal services are transitively exposed? ($R^+$ reverse dependency closure)
  * Which lockfiles resolved the bad version while it was live? ($[T_{publish}, T_{yank}]$ resolution window)
  * Which packages share maintainers or infrastructure? (Shared Maintainer ATO)
  * Are there typosquat packages nearby? (Damerau-Levenshtein distance + maintainer graph isolation)
* **Official Datasets & Evaluation:**
  * Ground truth drawn from **OSV.dev** and the **GitHub Advisory Database (GHSA)**.
  * Evaluated on precision, recall, query latency, and cost over held-out advisories.

#### Option B: Code Graphs for IDE Assistants
* **Core Problem:** Vector similarity search is a weak proxy for code context. Code requires AST call chains, type definitions, startup configs, and test mappings.
* **Official Datasets & Evaluation:**
  * **SWE-bench** (`swebench/SWE-bench`).
  * Scored on retrieval heuristics against a similarity-only baseline.

---

### Track 03: Memory + Context Retrieval
* **Core Problem:** Agent memory layer for cross-session continuity over chat histories spanning 30–40 sessions and 115,000+ tokens.
* **Hard Part:** Chronological reasoning, state overwrites/revisions, and correct abstention (knowing when information isn't present).
* **Official Datasets:**
  * `github.com/xiaowu0162/LongMemEval` (LongMemEval)
  * `github.com/xiaowu0162/LongMemEval-V2` (LongMemEval-V2)
  * `github.com/mohammadtavakoli78/BEAM` (BEAM - up to 10M tokens)
* **What Strong Work Shows:** Accuracy vector stores cannot reach; explicit time & revision handling; first-class abstention handling; real-world token/cost efficiency.
