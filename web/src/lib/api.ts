import type { AskResult, GraphExport, HistoryRow, RedwoodAnswer, SlackFormattedAnswer, StateResult } from "./contracts";

const API_BASE = process.env.NEXT_PUBLIC_CONTINUUM_API ?? "http://127.0.0.1:8080";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function healthCheck(): Promise<{ status: string; database?: string }> {
  return fetchJson("/health");
}

export async function askQuestion(question: string, questionId = "web-ad-hoc"): Promise<AskResult> {
  return fetchJson("/v1/ask", {
    method: "POST",
    body: JSON.stringify({ question, question_id: questionId }),
  });
}

export async function askFormatted(question: string): Promise<SlackFormattedAnswer> {
  return fetchJson("/v1/ask/formatted", {
    method: "POST",
    body: JSON.stringify({ question, question_id: "web-formatted" }),
  });
}

export async function exportGraph(entity: string, depth = 2): Promise<GraphExport> {
  return fetchJson(`/v1/graph/export?entity=${encodeURIComponent(entity)}&depth=${depth}`);
}

export async function fetchHistory(entity: string, predicate = "OWNS"): Promise<{ history?: HistoryRow[] }> {
  return fetchJson(`/v1/semantic/history?entity=${encodeURIComponent(entity)}&predicate=${predicate}`);
}

export async function fetchEvidence(entity: string, predicate = "OWNS"): Promise<StateResult> {
  return fetchJson(`/v1/semantic/evidence?entity=${encodeURIComponent(entity)}&predicate=${predicate}`);
}

export async function fetchConflicts(entity: string, predicate = "OWNS"): Promise<StateResult> {
  return fetchJson(`/v1/semantic/conflicts?entity=${encodeURIComponent(entity)}&predicate=${predicate}`);
}

export async function fetchCurrentState(entity: string, predicate = "OWNS"): Promise<StateResult> {
  return fetchJson(`/v1/semantic/state?entity=${encodeURIComponent(entity)}&predicate=${predicate}`);
}

// Redwood harness runs as a same-origin Vercel Python function by default.
const REDWOOD_API = process.env.NEXT_PUBLIC_REDWOOD_API ?? "/api/redwood";

export async function askRedwood(question: string): Promise<RedwoodAnswer> {
  const res = await fetch(REDWOOD_API, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`redwood ${res.status}`);
  return res.json() as Promise<RedwoodAnswer>;
}

export async function isRedwoodLive(): Promise<boolean> {
  try {
    const res = await fetch(REDWOOD_API, { cache: "no-store" });
    if (!res.ok) return false;
    const d = await res.json();
    return d?.status === "ok" && (d?.indexed ?? 0) > 0;
  } catch {
    return false;
  }
}

export async function isApiAvailable(): Promise<boolean> {
  try {
    const h = await healthCheck();
    return h.status === "ok";
  } catch {
    return false;
  }
}
