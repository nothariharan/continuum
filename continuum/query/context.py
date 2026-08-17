"""QueryContext — the canonical boundary object for the Continuum query path.

Every question, regardless of source, is decomposed into exactly one
QueryContext before any retrieval, traversal, or state resolution happens.
Downstream layers consume only this object — they never see raw source
format (Slack/Gmail/GitHub/Jira are invisible past this boundary).

Shape (all fields always present, unknown -> empty/default):

    QueryContext
    ├── query            raw question + id
    ├── intent           OWNERSHIP | ASSIGNMENT | LEADERSHIP | DECISION |
    │                    HISTORY | CONFLICT | PROVENANCE | DEPENDENCY |
    │                    CO_OCCURRENCE | ENTITY_RESOLUTION | GENERIC
    ├── entities         [{mention, role, type, canonical_key?}]
    ├── relationships    [{predicate, confidence, raw_hint}]
    ├── temporal         [TemporalConstraint]
    ├── candidates       {claims, entities, sources, artifacts}  (retrieval)
    ├── conflicts        [conflict records]                        (state)
    ├── provenance       [evidence items]                          (state)
    └── confidence       float | None

Contract rules:
- decomposition is deterministic and side-effect free
- mentions stay unresolved (canonical_key filled later by the entity bridge)
- temporal constraints are extracted from the question, never hardcoded
- the object is serializable (to_dict / from_dict) for tracing and tests
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

INTENTS = frozenset(
    {
        "OWNERSHIP",
        "ASSIGNMENT",
        "LEADERSHIP",
        "DECISION",
        "HISTORY",
        "CONFLICT",
        "PROVENANCE",
        "DEPENDENCY",
        "CO_OCCURRENCE",
        "ENTITY_RESOLUTION",
        "GENERIC",
    }
)

ROLES = frozenset({"subject", "object", "other"})

TEMPORAL_KINDS = frozenset(
    {"as_of", "before", "after", "current", "historical", "interval"}
)

# Graph-traversable predicates (schema.SUPPORTED_PREDICATES). Event
# predicates (e.g. DECIDED) are recognized as relationship hints for the
# intent/evidence layer but are not graph predicates yet.
GRAPH_PREDICATES = frozenset(
    {"OWNS", "MAINTAINS", "LEADS", "ASSIGNED_TO", "BLOCKS", "DEPENDS_ON", "REVIEWS"}
)


@dataclass(frozen=True)
class TemporalConstraint:
    """A time constraint lifted from the question text.

    kind:
      as_of      explicit point in time       ("as of 2026-06-01")
      before     strictly before a point      ("before the outage")
      after      strictly after a point       ("after the outage")
      current    present-tense query          ("who owns it now")
      historical past-tense query             ("who used to own it")
      interval   a stated range               ("during March 2026")
    value: ISO date (YYYY-MM-DD) when explicit, else None
    anchor: the event/keyword the constraint refers to, if any
    """

    kind: str
    value: str | None
    anchor: str | None
    raw: str


@dataclass(frozen=True)
class QueryEntity:
    mention: str
    role: str
    type: str = "person"
    canonical_key: str | None = None


@dataclass(frozen=True)
class QueryRelationship:
    predicate: str
    confidence: float = 0.8
    raw_hint: str = ""


@dataclass(frozen=True)
class CandidateScope:
    claims: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)


@dataclass
class QueryContext:
    """The stable object every query layer consumes and produces."""

    question_id: str = ""
    question: str = ""
    intent: str = "GENERIC"
    entities: list[QueryEntity] = field(default_factory=list)
    relationships: list[QueryRelationship] = field(default_factory=list)
    temporal: list[TemporalConstraint] = field(default_factory=list)
    candidates: CandidateScope = field(default_factory=CandidateScope)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    provenance: list[dict[str, Any]] = field(default_factory=list)
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "QueryContext":
        entities = [
            QueryEntity(**e) for e in payload.get("entities", [])
        ]
        relationships = [
            QueryRelationship(**r) for r in payload.get("relationships", [])
        ]
        temporal = [
            TemporalConstraint(**t) for t in payload.get("temporal", [])
        ]
        candidates = CandidateScope(**payload.get("candidates", {}))
        return cls(
            question_id=payload.get("question_id", ""),
            question=payload.get("question", ""),
            intent=payload.get("intent", "GENERIC"),
            entities=entities,
            relationships=relationships,
            temporal=temporal,
            candidates=candidates,
            conflicts=payload.get("conflicts", []),
            provenance=payload.get("provenance", []),
            confidence=payload.get("confidence"),
        )

    def graph_predicates(self) -> list[str]:
        """Relationship hints that map to traversable graph predicates."""
        return [r.predicate for r in self.relationships if r.predicate in GRAPH_PREDICATES]