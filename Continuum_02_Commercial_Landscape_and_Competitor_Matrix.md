# Continuum: Commercial Landscape & Competitor Capability Matrix (2025–2026)

> **Document Version:** 1.0  
> **Project:** `Continuum` (Enterprise Bitemporal Truth Engine)  
> **Source Material:** Agent Group 1 & 2 Commercial Research Stream  

---

## 1. Executive Summary & Macro Landscape Dynamics

The enterprise knowledge landscape has undergone a foundational shift between 2024 and 2026: **1st-generation RAG (flat text chunking + naive vector embedding search) has failed in high-complexity enterprise environments.** 

Traditional RAG suffers from severe enterprise failure modes:
1. **The "Amnesia" & Temporal Blindness Problem:** Inability to handle temporal state (e.g., distinguishing between a 2023 Q3 budget draft and the finalized 2025 Q1 strategy document).
2. **Permission Realignment Shock:** Surfacing over-shared or confidential documents when ACL (Access Control List) synchronization lags behind source platforms.
3. **Multi-Hop Traversal Failure:** Inability to resolve relationships across multi-system boundaries (e.g., linking a Jira ticket to a Slack discussion, a GitHub PR, and a Customer Salesforce Deal).

To solve this, the market has bifurcated into four distinct architectural tiers:

1. **Horizontal Enterprise Search & "Company Brains":** Tools like **Glean**, **Microsoft 365 Copilot**, **Google Workspace/Gemini Enterprise**, **Notion AI**, **Dust.tt**, **Sana AI**, **Dropbox Dash**, **Box AI**, and **Guru**.
2. **Workflow-Embedded & Action-Oriented AI Agents:** Platforms like **Atlassian Rovo**, **Moveworks**, **ServiceNow AI**, **Salesforce Agentforce**, **Slack AI**, and **Hebbia Matrix**.
3. **Data Lakehouse & Enterprise Infrastructure Engines:** Deep data/ontology platforms like **Palantir Foundry/AIP**, **Databricks IQ/Agent Studio**, and **Snowflake Cortex/Horizon**.
4. **Emerging 2025-2026 Open-Source & Startup Context Graph / Memory Primitives:** Next-generation frameworks like **Graphiti (Zep)**, **Mem0**, **Cognee**, **Letta (MemGPT)**, **Kuzu**, **Qdrant / Neo4j Property Graphs**, and **Unstructured**.

---

## 2. Comprehensive Competitor Capability Matrix (Top 18 Platforms)

| Vendor / Platform | Target Persona & Core Problem | Supported Connectors & Ingestion | Knowledge Graph vs Vector Only | Entity Resolution & Alias Handling | Contradiction & Temporal Handling | Permissions & ACL Enforcement Model | Provenance & Multi-Hop Capabilities | Real User Complaints & Product Weaknesses |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Glean** | Enterprise workers; universal search & workspace knowledge | 100+ native connectors (Slack, Jira, Drive, GMail, SFDC, Confluence) | **Hybrid Graph + Vector:** Persistent Knowledge Graph + Personal Graph | Cross-system identity mapping via OAuth/email heuristics | Document timestamp weighting; struggles with fine-grained fact contradictions | Real-time inherited ACL pre-filtering per query; single-tenant execution | High (triplet traversal: User $\rightarrow$ Ticket $\rightarrow$ Doc); citation linked | High per-seat cost (\$30-\$50+/mo); graph latency on massive tenants; ACL sync lag |
| **Microsoft 365 Copilot** | M365 Enterprise users; productivity across Word, Excel, Teams | Native M365 stack + Graph Connectors (limited 3rd party) | **Microsoft Graph + Semantic Index:** Vector index over Graph triples | M365 Entra ID (Azure AD) unified identity layer | Version history timestamp ranking; basic recency bias | Delegated user security context (strictly mirrors SharePoint/OneDrive ACLs) | Moderate multi-hop across M365 app boundaries; citation snippets | Disastrous data exposure from legacy over-shared SharePoint folders; slow indexing |
| **Google Gemini Enterprise** | Workspace users; search & document intelligence across Drive/Gmail | Google Workspace native + Vertex AI Search Connectors | **Vertex AI Search:** Hybrid vector + structured metadata search | Google Workspace ID / Identity API lookup | Document freshness scoring; limited explicit edge retraction | Workspace OAuth scope delegation & IAM access policies | Moderate (Vertex AI Agent Builder multi-agent chaining) | Product re-branding confusion; "black box" chunking; non-deletable chat history risk |
| **Atlassian Rovo** | Software & Ops teams; linking Jira, Confluence, Loom, Code | 50-100+ connectors (Jira, Confluence, GitHub, Slack, Figma) | **Teamwork Graph:** Structured GraphQL graph layer | Maps user handles across Jira, Bitbucket, GitHub, Slack | Activity stream recency; status-based workflow resolution | Inherits Atlassian site permissions + 3rd party OAuth scopes | High multi-hop between issues, PRs, docs, and team owners; MCP supported | Shallow code intelligence vs. Cursor; strict dependency on clean Jira metadata; RovoBlast vulnerability |
| **Hebbia (Matrix)** | PE, Investment Banking, Legal; multi-doc financial audit | FactSet, PitchBook, SharePoint, Box, custom PDF/Excel drop | **Iterative Source Decomposition (ISD):** Document-table matrix | Named Entity Recognition (NER) across tabular and text data | Manual version selection; cell-based audit verification | Role-based tenant isolation; document-level access controls | High multi-step tabular analysis via agent swarms; cell-level source citations | High hallucination in numerical multi-step math; expensive per-user licensing; "wrapper" sentiment |
| **Sana AI** | Enterprise HR, IT, & Knowledge Management | Slack, Google Drive, Notion, SharePoint, HRIS | **Process Graph + Governed Context:** Structural RAG | Cross-app user identity & department mapping | Document modification timestamps; version comparison | Granular workspace role access; inherited document ACLs | Multi-step agent workflow execution; source passage attribution | Black-box chunking limits fine-tuning; friction with legacy on-prem systems; agent sprawl |
| **Dust.tt** | Tech-forward teams; custom multiplayer AI workspace | Slack, Notion, GitHub, Google Drive | **Workspace-Scoped RAG:** Multi-model vector indices | Simple metadata matching across workspace connections | Manual agent prompt context updates; basic recency filters | Workspace and folder-level access control permissions | Multi-agent delegation; assistant-to-assistant prompt chaining | Lacks automated native entity-relationship knowledge graph; manual agent tuning required |
| **Moveworks** | Enterprise IT & HR service desk (Acquired by ServiceNow 2025) | ServiceNow, Workday, Jira, Salesforce, Okta | **Dynamic Enterprise Graph:** Action-oriented entity model | Deep HRIS/Okta entity resolution for employees & assets | Incident state machine tracking; real-time ticket updates | Enterprise IAM / SSO pre-filtered access per user session | Multi-step ITSM/HR action execution across platforms | Extremely expensive; long implementation timelines; weak for generic text search |
| **ServiceNow AI (Now Assist)** | Enterprise IT Service Management & Workflow leads | Native ServiceNow CMDB, Knowledge Base, external APIs | **CMDB Knowledge Graph:** Configuration item relationship map | ServiceNow Sys_ID & CMDB entity mapping | Operational state machine updates; IT incident status tracking | ServiceNow ACL governance engine (role & record-level) | High workflow orchestration across ITIL processes | Siloed strictly to ServiceNow; poor non-ServiceNow document discovery; heavy setup costs |
| **Salesforce Agentforce** | CRM, Sales, & Customer Support teams | Salesforce Data Cloud, MuleSoft connectors, S3 | **Atlas Reasoning Engine + Data Cloud Graph** | Unified Contact/Account ID mapping via Data Cloud | Real-time Data Cloud record ingestion & state tracking | Salesforce Object & Field-Level Security (FLS) enforcement | Action-driven workflow multi-hop across CRM records & external APIs | High per-conversation cost; acts as frustrating customer chatbot gatekeeper if un-tuned |
| **Slack AI** | Knowledge workers collaborating inside Slack | Slack channels, canvases, threads (limited external) | **Channel Vector Search:** Message & thread embedding index | Slack User ID & channel tagging | Thread timestamp sorting; recency-boosted search | Inherits Slack channel membership access (Public/Private) | Low (thread context synthesis only); channel link citations | Siloed to Slack text; lacks external graph connections; expensive add-on pricing |
| **Notion AI** | Teams using Notion as internal wiki & workspace | Native Notion pages + Google Drive, Slack, Jira connectors | **Notion Workspace Index:** Hybrid vector search | Notion User ID & page reference links | Page edit history & database property tracking | Notion page and workspace-level permission inheritance | Moderate (Q&A across workspace pages & connected sources) | Gated behind business plans; lacks multi-hop entity graph; search latency across connectors |
| **Guru** | Support & Operations teams needing verified answers | Slack, Google Drive, Zendesk, Salesforce | **Verified Knowledge Network:** Card-based curated index | Tag & card metadata mapping | **Human-in-the-loop verification:** Card expiration dates | Board & Collection level permissions; SSO integration | Low-to-moderate; verified card retrieval with author attribution | High human maintenance overhead; if cards aren't verified by staff, search relevancy tanks |
| **Dropbox Dash** | Individual knowledge workers & small teams | Dropbox, Google Workspace, M365, Notion, Asana | **Universal Content Index:** Desktop/browser context RAG | Desktop & cloud user account identity binding | File modification date sorting | OAuth permission mirroring per user token | Low (passage retrieval across connected apps) | Surface-level RAG; lacks deep enterprise entity graph; sync glitches across enterprise SSO |
| **Box AI** | Enterprise content management & compliance teams | Box Content Cloud native files (PDF, Word, Images) | **Box Graph & Metadata Index:** Document content embeddings | Box User ID & enterprise metadata attributes | Document versioning history within Box | Enterprise-grade Box access policies & retention rules | Moderate (Q&A across Box document repositories) | Locked strictly to Box files; weak external connector capabilities; no cross-app graph |
| **Palantir AIP** | Defense, Intelligence, Enterprise Ops, Supply Chain | ERPs, SQL, Cloud Storage, IoT sensors, APIs | **Dynamic Enterprise Ontology:** Digital twin of business operations | Advanced pipeline-level identity resolution & entity linking | **Conflict Resolution Engine:** Object timestamp & action history | Granular cell-level & object-level security marking (Control Marking) | **Exceptional:** Graph traversal, simulation, and automated action execution | Steep learning curve; multi-million dollar contracts; extreme platform lock-in |
| **Databricks IQ** | Data Engineers, Data Scientists, Analytics teams | Delta Lake, Unity Catalog, Data Warehouses, Vector Search | **Unity Catalog Knowledge Mesh:** Schema & lineage graph | Unity Catalog metastore entity resolution | Data versioning via Delta Lake Time Travel | Unity Catalog governed access control (Table/Row/Column) | High SQL & data lineage multi-hop reasoning via Mosaic AI | Focused on structured data analytics; weak for conversational search (Slack/Wikis) |
| **Snowflake Cortex** | Data Analysts & Enterprise Data Cloud teams | Snowflake Data Cloud, Iceberg tables, Stage files | **Cortex Search + Horizon:** Hybrid search over Data Cloud | Snowflake account schema object mapping | Table change tracking (CDC) & dynamic tables | Snowflake Horizon unified governance & RBAC model | High analytical multi-hop SQL generation & RAG function calls | Requires building custom graph layers for unstructured text; heavy SQL orientation |

---

## 3. Startup Landscape Map: 2025–2026 Context Graphs & Agent Memory

```
                           +-------------------------------------------------------+
                           |  2025-2026 ENTERPRISE CONTEXT GRAPH & AGENT MEMORY   |
                           +-------------------------------------------------------+
                                                       |
         +-------------------------+-------------------+-------------------------+
         |                         |                                             |
+------------------+     +-------------------+                         +-------------------+
| TEMPORAL KNOWLEDGE |     | SEMANTIC MEMORY   |                         | AGENT RUNTIME     |
| GRAPH PRIMITIVES  |     | LAYERS            |                         | MEMORY SYSTEMS    |
+------------------+     +-------------------+                         +-------------------+
| • Graphiti (Zep) |     | • Mem0            |                         | • Letta (MemGPT)  |
| • Cognee         |     | • Unstructured    |                         | • LangMem         |
+------------------+     +-------------------+                         +-------------------+
         |                         |                                             |
         +-------------------------+-------------------+-------------------------+
                                                       |
                                         +---------------------------+
                                         | GRAPH ENGINE & RAG STACK  |
                                         +---------------------------+
                                         | • Kuzu (Embedded Graph)   |
                                         | • Neo4j Property Graph    |
                                         | • Qdrant Hybrid GraphRAG  |
                                         +---------------------------+
```

### Deep Taxonomy of Emerging 2025-2026 Frameworks

1. **Graphiti (by Zep): Bi-Temporal Knowledge Graph for AI Agents**
   - **Core Philosophy:** Implements a bi-temporal graph model distinguishing between *Event Time* (when a fact occurred in the real world) and *Transaction Time* (when the fact was recorded by the system).
   - **Key Innovation:** Automatically handles fact updating, contradiction invalidation (edge retraction), and dynamic entity state over time without requiring full graph re-indexing.
2. **Mem0: The Universal Distributed Memory Layer**
   - **Core Philosophy:** Lightweight, low-latency memory tier combining vector storage, key-value state, and graph nodes for user-level and agent-level personalization.
   - **Key Innovation:** Fast API-driven insertion and retrieval of user preferences, short-term session state, and entity memories across agentic interactions.
3. **Cognee: Graph-Native ECL (Extract, Cognify, Load) Engine**
   - **Core Philosophy:** Replaces classic ETL pipelines with an AI-driven ECL framework that transforms unstructured documents into a structured property graph.
   - **Key Innovation:** Automates graph topology generation, extracting concepts, entities, and relationships directly into graph storage engines (like Neo4j or Kuzu).
4. **Letta (formerly MemGPT): Agent-Managed Tiered OS Memory**
   - **Core Philosophy:** Models agent memory as an Operating System memory hierarchy (Core RAM vs. Archival Disk Storage).
   - **Key Innovation:** Empowers the LLM agent to autonomously read, edit, append, and search its own persistent memory banks using explicit self-directed tool calls.
5. **Kuzu & Neo4j Property Graph RAG Engine Infrastructure**
   - **Core Philosophy:** Embedded (Kuzu) and distributed (Neo4j) property graph databases optimized for hybrid GraphRAG.
   - **Key Innovation:** Integrates vector embeddings directly onto graph nodes and edges, allowing vector similarity search to act as the entry point for multi-hop graph traversal.

---

## 4. White Space Strategy for `Continuum`

Incumbents like Glean, Microsoft, and Salesforce are constrained by legacy enterprise software architectures:
- They use **proprietary, black-box RAG pipelines** that cannot be customized for domain-specific knowledge.
- They struggle with **temporal state and fact invalidation**, treating documents as static text blobs rather than dynamic temporal facts.
- Their per-seat SaaS pricing models make full-company deployment prohibitively expensive.

`Continuum` disrupts them by combining:
1. **Bi-Temporal Property Graph Architecture (HydraDB Engine)** to natively handle fact updates, dynamic temporal queries, and edge retraction out of the box.
2. **Model Context Protocol (MCP) First Integration** to expose the Company Brain as an open **MCP Server** for Claude Code, Cursor, and enterprise agents.
3. **Local-First / Self-Hostable Privacy Architecture** running inside corporate VPCs without multi-tenant security leakage.
