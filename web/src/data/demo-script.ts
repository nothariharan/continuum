import type { ConnectorDef, GraphExport } from "@/lib/contracts";

export const CONNECTORS: ConnectorDef[] = [
  { id: "slack", name: "Slack", status: "connected" },
  { id: "gmail", name: "Gmail", status: "planned" },
  { id: "linear", name: "Linear", status: "planned" },
  { id: "github", name: "GitHub", status: "planned" },
  { id: "drive", name: "Google Drive", status: "planned" },
  { id: "notion", name: "Notion", status: "planned" },
  { id: "jira", name: "Jira", status: "planned" },
  { id: "confluence", name: "Confluence", status: "planned" },
];

export const DEMO_GRAPH: GraphExport = {
  entity: "account:acme",
  nodes: [
    { id: "account:acme", label: "Account", name: "Acme", type: "entity" },
    { id: "person:morgan", label: "Person", name: "Morgan", type: "person" },
    { id: "person:priya", label: "Person", name: "Priya", type: "person" },
    { id: "person:sarah", label: "Person", name: "Sarah", type: "person" },
    { id: "artifact:slack-handoff", label: "Artifact", name: "Slack handoff thread", type: "artifact", source: "slack" },
    { id: "artifact:gmail-handoff", label: "Artifact", name: "Gmail handoff notice", type: "artifact", source: "gmail" },
    { id: "artifact:linear-update", label: "Artifact", name: "Linear ownership update", type: "artifact", source: "linear" },
    { id: "source:slack", label: "Source", name: "Slack", type: "source" },
    { id: "source:gmail", label: "Source", name: "Gmail", type: "source" },
    { id: "source:linear", label: "Source", name: "Linear", type: "source" },
  ],
  edges: [
    { source: "person:morgan", target: "account:acme", predicate: "OWNS" },
    { source: "person:priya", target: "account:acme", predicate: "OWNS" },
    { source: "person:sarah", target: "account:acme", predicate: "OWNS" },
    { source: "artifact:slack-handoff", target: "source:slack", predicate: "FROM" },
    { source: "artifact:gmail-handoff", target: "source:gmail", predicate: "FROM" },
    { source: "artifact:linear-update", target: "source:linear", predicate: "FROM" },
  ],
};

export type DemoStep =
  | { kind: "ask"; question: string }
  | { kind: "investigate"; sources: string[] }
  | { kind: "answer"; text: string; owner: string }
  | { kind: "history"; from: string; to: string }
  | { kind: "evidence"; items: string[] }
  | { kind: "graph"; highlight: string }
  | { kind: "memory_event"; message: string }
  | { kind: "update"; owner: string };

export const DEMO_SCRIPT: DemoStep[] = [
  { kind: "ask", question: "Who owns Acme now?" },
  { kind: "investigate", sources: ["slack", "gmail", "linear"] },
  { kind: "answer", text: "Priya owns Acme now.", owner: "Priya" },
  { kind: "history", from: "Morgan", to: "Priya" },
  { kind: "evidence", items: ["Slack handoff thread", "Gmail notice", "Linear update"] },
  { kind: "graph", highlight: "account:acme" },
  { kind: "memory_event", message: "Sarah takes over Acme." },
  { kind: "update", owner: "Sarah" },
  { kind: "ask", question: "Who owns Acme now?" },
  { kind: "answer", text: "Sarah owns Acme now.", owner: "Sarah" },
];

export const DEMO_ANSWER_BEFORE = {
  question: "Who owns Acme now?",
  answer: "Priya owns Acme now.",
  previous: "Morgan",
  effective: "Aug 1",
  sources: ["Slack", "Gmail", "Linear"],
  status: "definitive" as const,
};

export const DEMO_ANSWER_AFTER = {
  question: "Who owns Acme now?",
  answer: "Sarah owns Acme now.",
  previous: "Priya",
  effective: "Today",
  sources: ["Slack"],
  status: "definitive" as const,
};
