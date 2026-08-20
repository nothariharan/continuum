/** Mirrors continuum.benchmark.contract — shared UI/API contract. */

export type AnswerStatus = "definitive" | "absent" | "conflict" | "error" | "review";

export interface StateValue {
  entity_id?: string;
  name?: string;
  subject_name?: string;
}

export interface StateResult {
  entity_id?: string;
  predicate?: string;
  status?: AnswerStatus;
  value?: StateValue | null;
  valid_from?: string | null;
  valid_to?: string | null;
  confidence?: number;
  history?: HistoryRow[];
  resolution?: string;
  conflicting_subjects?: string[];
  claims?: Record<string, unknown>[];
  evidence?: EvidenceItem[];
}

export interface EvidenceItem {
  claim_id?: string;
  subject_mention?: string;
  object_mention?: string;
  artifact_id?: string;
  artifact_kind?: string;
  source_id?: string;
  source?: string;
  observed_at?: string;
  timestamp?: string;
}

export interface AskResult {
  question_id: string;
  question: string;
  status: AnswerStatus;
  answer: string | null;
  resolved_entities: string[];
  claims_used: string[];
  state_result: StateResult;
  conflicts: unknown[];
  evidence: EvidenceItem[];
  layers: Record<string, unknown>;
  context: Record<string, unknown>;
  latency_ms: Record<string, number>;
  diagnostics: Record<string, boolean | null>;
  query_context?: Record<string, unknown>;
  trace: string[];
}

export interface HistoryRow {
  subject_id: string;
  subject_name: string;
  valid_from?: string | null;
  valid_to?: string | null;
}

export interface GraphNode {
  id: string;
  label: string;
  name: string;
  type: "entity" | "person" | "artifact" | "source" | "claim";
  source?: string;
  dsid?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  predicate: string;
  claim_id?: string;
}

export interface GraphExport {
  entity: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface SlackFormattedAnswer {
  text: string;
  blocks: Record<string, unknown>[];
}

export type ConnectorStatus = "connected" | "demo" | "planned";

export interface ConnectorDef {
  id: string;
  name: string;
  status: ConnectorStatus;
}

/** Live Redwood harness response (BM25 retrieval + Fireworks answer). */
export interface RedwoodEvidence {
  id: string;
  source: string;
  source_name: string;
  title: string;
  snippet: string;
}
export interface RedwoodAnswer {
  answer: string | null;
  abstain: boolean;
  evidence: RedwoodEvidence[];
  sources: string[];
  trace: {
    retrieval_ms?: number;
    generation_ms?: number;
    total_ms?: number;
    candidates?: number;
    sources_searched?: string[];
    evidence_count?: number;
    error?: string;
  };
}
