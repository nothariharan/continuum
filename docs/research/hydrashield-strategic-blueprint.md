# Project Blueprint: HydraShield (Track 2A Supply Chain Radar)

> **Document Version:** 1.0  
> **Project Name:** `HydraShield` (or `BlastRadius.ai`)  
> **Target Track:** Track 02 — Repos, Dependencies & Code as Graphs (Option A: Supply Chain Blast Radius)  
> **Target Award:** Grand Champion ($5,000) & Best Use of HydraDB ($500)

---

## 1. Project Concept & Pitch Narrative

**`HydraShield`** is a real-time software supply chain blast radius calculator and temporal security auditing engine powered by **HydraDB**. 

When a malicious package version is published (e.g., the TanStack compromise, CVE-2026-45321), security teams face a critical race against time: **"Which of our 50 production microservices are exposed right now, and which build pipelines resolved the compromised version while it was live?"**

Traditional security tools (`npm audit`, Snyk, Dependabot) inspect repositories in isolation. Flat vector databases cannot compute graph traversals. **HydraShield** ingests ecosystem dependency graphs and production lockfile deployments into HydraDB, executing **reverse transitive closure traversals ($R^+$)** and **temporal point-in-time lockfile audits** in milliseconds.

---

## 2. Graph Schema Specification

```
  (Maintainer) ---[:MAINTAINS]---> (Package)
       |                              ^
  [:PUBLISHED]                  [:DEPENDS_ON {semver}]
       v                              |
   (Version) -------------------------+
       ^
  [:RESOLVED_LOCKFILE {installed_at}]
       |
   (Service) <--- [:AFFECTS] --- (Advisory)
```

### 2.1 Node Schemas

1. **`Package` Node**
   * `id`: `"npm:react-query"` | `"pypi:requests"`
   * `name`: `"react-query"`
   * `ecosystem`: `"npm"`
   * `latest_version`: `"5.28.1"`

2. **`Version` Node**
   * `id`: `"npm:react-query@5.28.1"`
   * `package_id`: `"npm:react-query"`
   * `version_str`: `"5.28.1"`
   * `published_at`: `"2026-05-11T09:00:00Z"`
   * `shasum`: `"a1b2c3d4e5f6..."`

3. **`Maintainer` Node**
   * `id`: `"maintainer:npm:tanstack-bot"`
   * `username`: `"tanstack-bot"`
   * `email`: `"dev@tanstack.com"`
   * `account_created_at`: `"2024-01-15T00:00:00Z"`

4. **`Advisory` Node**
   * `id`: `"GHSA-xxxx-yyyy-zzzz"`
   * `cve_id`: `"CVE-2026-45321"`
   * `severity`: `"CRITICAL"`
   * `summary`: `"Malicious token harvester injected via GitHub Actions OIDC breach"`

5. **`Service` Node** *(Simulated Microservices)*
   * `id`: `"service:auth-service"`
   * `repo_name`: `"enterprise/auth-service"`
   * `owner_team`: `"security-ops"`

---

### 2.2 Edge Schemas

1. **`DEPENDS_ON` Edge (`Version` $\rightarrow$ `Package`):** `semver_range: "^5.0.0"`, `is_dev_dependency: false`
2. **`MAINTAINS` Edge (`Maintainer` $\rightarrow$ `Package`):** `role: "owner"`
3. **`PUBLISHED` Edge (`Maintainer` $\rightarrow$ `Version`):** `published_at: "2026-05-11T09:00:00Z"`
4. **`RESOLVED_LOCKFILE` Edge (`Service` $\rightarrow$ `Version`):** `installed_at: "2026-05-11T09:04:00Z"`, `lockfile_type: "package-lock.json"`
5. **`AFFECTS` Edge (`Advisory` $\rightarrow$ `Version`):** `patched_in: "5.28.2"`

---

## 3. Four Essential Demo Queries

### Query 1: Transitive Reverse Dependency Blast Radius ($R^+$)
* **Goal:** Given `npm:malicious-pkg@1.0.0`, return all transitively exposed internal services across multi-hop dependency chains.
* **Traversal:** Recursively follow incoming `DEPENDS_ON` and `RESOLVED_LOCKFILE` edges, evaluating SemVer compatibility at each hop.

### Query 2: Lockfile Resolution Window Temporal Audit
* **Goal:** Identify which production builds executed `npm install` during the live vulnerability window $[T_{publish}, T_{yank}]$.
* **Traversal:** Filter `RESOLVED_LOCKFILE` edges where $T_{publish} \le \text{installed\_at} \le T_{yank}$. *(Demonstrates HydraDB's temporal versioning feature).*

### Query 3: Shared Maintainer Account Takeover (ATO) Radius
* **Goal:** If maintainer account `tanstack-bot` is compromised, list all co-maintained packages and calculate overall ecosystem risk.

### Query 4: Typosquatting Proximity Warning
* **Goal:** Detect newly published packages with high name similarity (Damerau-Levenshtein distance $\le 2$) paired with zero maintainer graph overlap.

---

## 4. 9-Day Implementation Roadmap

```
  [Days 1-2] : Ingestion Pipeline (npm/OSV parser -> HydraDB Graph)
  [Days 3-4] : Graph Query Engine (Reverse transitive closure, temporal audit)
  [Days 5-6] : Interactive Web/CLI Dashboard (Zero-Day Alert Visualizer)
  [Days 7-8] : End-to-End Scenario Testing & README Documentation
  [Day 9]    : 3-Minute Video Recording & Final Submission Form
```

---

## 5. Outline for the 3-Minute Submission Video

1. **The Problem (0:00 - 0:45):** "When a supply chain attack strikes npm, how fast can you calculate which of your 50 services are exposed? Flat vector DBs and `npm audit` fail here."
2. **The Project (0:45 - 1:15):** "Introducing HydraShield, powered by HydraDB's Git-styled temporal graph and object storage."
3. **The Live Demo (1:15 - 2:15):** "Watch us trigger a simulated zero-day attack on `@tanstack/react-query`. In milliseconds, HydraShield traverses reverse dependencies, flags exposed microservices, and runs a temporal audit on compromised lockfile builds."
4. **Why HydraDB (2:15 - 3:00):** "HydraDB's temporal edge graphs and sub-millisecond traversals make this graph-native security auditing possible."
