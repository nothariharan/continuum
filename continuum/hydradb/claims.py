"""Claim ingestion boundary: validated claims + manual resolutions -> HydraDB.

This is the founder-owned side of the Phase 2B pipeline. It consumes the
shared contract (JSONL claims validated against `continuum.claims`) and a
manual resolution map (mention text -> entity key/label), then writes the
Phase 1 graph shape: entity nodes, Claim nodes, SOURCED_FROM / ABOUT /
predicate / CONTRADICTS relationships. Mentions stay unresolved on the Claim
node itself; the resolution map is Phase 2B's "manually resolvable entities"
scope. Automatic resolution is Phase 3.

HydraDB constraints honored:
- numeric internal ids (Phase 2B uses its own id range: 1_000_000_000_000+)
- MERGE on `id` only, labels via SET
- scalar parameters only (no lists/maps)
- chunked, id-range-scoped deletes for reset
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Iterable, Mapping

from continuum.claims import SUPPORTED_PREDICATES, Claim, ContractError
from continuum.hydradb import HydraDBClient

OPEN_END = "9999-12-31"
ID_OFFSET = 1_000_000_000_000
ID_SPAN = 10_000

PREDICATE_RELS = tuple(sorted(SUPPORTED_PREDICATES))
ENTITY_LABELS = ("Person", "Account", "Project", "Service", "Team")

# Canonical predicate/entity constraints: a claim is graph-loadable only when
# the resolved subject/object label pair is allowed for the predicate.
# This is the explicit encoding of "without inventing entities" — a claim
# whose mentions cannot resolve to a compatible pair is not graph-loadable.
ENTITY_PAIR_RULES: dict[str, frozenset[tuple[str, str]]] = {
    "OWNS": frozenset({("Person", "Account"), ("Person", "Project")}),
    "MAINTAINS": frozenset({("Person", "Account"), ("Person", "Project"), ("Person", "Service"), ("Team", "Service")}),
    "LEADS": frozenset({("Person", "Account"), ("Person", "Project"), ("Person", "Team")}),
    "ASSIGNED_TO": frozenset({("Person", "Account"), ("Person", "Project")}),
    "REVIEWS": frozenset({("Person", "Account"), ("Person", "Project")}),
    "BLOCKS": frozenset({("Person", "Project"), ("Project", "Project")}),
    "DEPENDS_ON": frozenset({("Project", "Project"), ("Project", "Service"), ("Service", "Service")}),
}


def pair_supported(predicate: str, subject_label: str, object_label: str) -> bool:
    """True when (predicate, subject_label, object_label) is canonical."""
    return (subject_label, object_label) in ENTITY_PAIR_RULES.get(predicate, frozenset())

CREATE_ENTITIES = """
UNWIND $rows AS row
MERGE (n {{id: row.id}})
SET n:{label},
    n.key = row.key,
    n.name = row.name,
    n.aliases = row.aliases
"""

CREATE_ARTIFACT_FIXTURE = """
UNWIND $rows AS row
MERGE (a {id: row.id})
SET a:Artifact,
    a.key = row.key,
    a.kind = row.kind,
    a.observed_at = row.observed_at,
    a.content = row.content,
    a.title = row.title,
    a.source_id = row.source_id
"""

CREATE_SOURCE_FIXTURE = """
UNWIND $rows AS row
MERGE (s {id: row.id})
SET s:Source,
    s.key = row.key,
    s.name = row.name
"""

CREATE_CLAIMS = """
UNWIND $rows AS row
MERGE (c {id: row.id})
SET c:Claim,
    c.key = row.key,
    c.artifact_id = row.artifact_id,
    c.subject_mention = row.subject_mention,
    c.predicate = row.predicate,
    c.object_mention = row.object_mention,
    c.subject_id = row.subject_id,
    c.subject_name = row.subject_name,
    c.object_id = row.object_id,
    c.observed_at = row.observed_at,
    c.valid_from = row.valid_from,
    c.valid_to = row.valid_to,
    c.confidence = row.confidence,
    c.extraction_method = row.extraction_method,
    c.evidence_span = row.evidence_span
"""

RELATE_SOURCED_FROM = """
UNWIND $rows AS row
MATCH (c:Claim {id: row.source}), (a:Artifact {id: row.target})
CREATE (c)-[:SOURCED_FROM]->(a)
"""

RELATE_REAL_SOURCE = """
UNWIND $rows AS row
MATCH (a:Artifact {id: row.source}), (s:Source {id: row.target})
CREATE (a)-[:FROM]->(s)
"""

RELATE_ABOUT = """
UNWIND $rows AS row
MATCH (c:Claim {{id: row.source}}), (e:{olabel} {{id: row.target}})
CREATE (c)-[:ABOUT]->(e)
"""

RELATE_PREDICATE = """
UNWIND $rows AS row
MATCH (s:{slabel} {{id: row.source}}), (o:{olabel} {{id: row.target}})
CREATE (s)-[:{rel}]->(o)
"""

SET_PREDICATE_VALIDITY = """
MATCH (s:{slabel} {{id: $source}})-[r:{rel}]->(o:{olabel} {{id: $target}})
SET r.valid_from = $valid_from, r.valid_to = $valid_to
"""

RELATE_FROM = """
UNWIND $rows AS row
MATCH (a:Artifact {id: row.source}), (s:Source {id: row.target})
CREATE (a)-[:FROM]->(s)
"""

RELATE_CONTRADICTS = """
UNWIND $rows AS row
MATCH (a:Claim {id: row.source}), (b:Claim {id: row.target})
CREATE (a)-[:CONTRADICTS]->(b)
"""

DELETE_PHASE2B = """
MATCH (n:{label})
WHERE n.id >= $min_id AND n.id < $max_id
DETACH DELETE n
"""

READ_DSID_ARTIFACTS = """
MATCH (a:Artifact)
WHERE a.dsid STARTS WITH 'dsid_'
RETURN a.dsid AS dsid, a.id AS id, a.timestamp AS timestamp, a.source AS source
"""

READ_CLAIM = """
MATCH (c:Claim {key: $key})
RETURN c.key AS key, c.artifact_id AS artifact_id,
       c.subject_mention AS subject_mention, c.predicate AS predicate,
       c.object_mention AS object_mention, c.subject_id AS subject_id,
       c.subject_name AS subject_name, c.object_id AS object_id,
       c.observed_at AS observed_at, c.valid_from AS valid_from,
       c.valid_to AS valid_to, c.confidence AS confidence,
       c.extraction_method AS extraction_method, c.evidence_span AS evidence_span
"""

READ_ALL_CLAIMS = """
MATCH (c:Claim)
WHERE c.id >= $min_id AND c.id < $max_id
RETURN c.id AS id, c.key AS key ORDER BY c.id
"""

COUNT_CLAIMS = """
MATCH (c:Claim)
WHERE c.id >= $min_id AND c.id < $max_id
RETURN count(*) AS n
"""


@dataclass(frozen=True)
class LoadResult:
    claims_attempted: int
    claims_written: int
    artifacts: int
    sources: int
    entities: int
    relationships: int
    load_ms: float
    read_back_ms: float
    read_back_count: int
    mismatches: int


def _next_ids(count: int, offset: int = ID_OFFSET) -> list[int]:
    return [offset + index for index in range(count)]


def resolve_mentions(claims: list[Claim], resolutions: Mapping[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Map claim mention strings to resolved entity definitions (manual, Phase 2B).

    Returns {mention_text: {key, name, label, aliases}}; raises ContractError
    for any mention that has no manual resolution. Resolution keys with no
    claims are ignored (abstention targets stay resolvable but unclaimed).
    """
    entity_by_mention: dict[str, dict[str, Any]] = {}
    for entity_key, definition in resolutions.items():
        label = str(definition.get("label", ""))
        if label not in ENTITY_LABELS:
            raise ContractError(f"resolution '{entity_key}': label must be one of {ENTITY_LABELS}, got {label!r}")
        for mention in definition.get("mentions", []):
            if mention in entity_by_mention:
                raise ContractError(
                    f"mention {mention!r} resolves to both '{entity_by_mention[mention]['key']}' and '{entity_key}'"
                )
            entity_by_mention[mention] = {
                "key": entity_key,
                "name": definition.get("name") or entity_key,
                "label": label,
                "aliases": "|".join(definition.get("aliases", []) or []),
            }
    missing: set[str] = set()
    for claim in claims:
        for mention in (claim.subject_mention, claim.object_mention):
            if mention not in entity_by_mention:
                missing.add(mention)
    if missing:
        raise ContractError(f"no manual resolution for {len(missing)} mention(s): {sorted(missing)}")
    return entity_by_mention


def _validity_overlap(a: dict[str, Any], b: dict[str, Any]) -> bool:
    a_to = a["valid_to"] or OPEN_END
    b_to = b["valid_to"] or OPEN_END
    return a["valid_from"] <= b_to and a_to > b["valid_from"]


def _contradiction_pairs(resolved: list[dict[str, Any]]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for index, a in enumerate(resolved):
        for b in resolved[index + 1 :]:
            if (
                a["object_id"] == b["object_id"]
                and a["predicate"] == b["predicate"]
                and a["subject_id"] != b["subject_id"]
                and _validity_overlap(a, b)
            ):
                pairs.append((a["claim_id"], b["claim_id"]))
    return pairs


def _delete_phase2b_graph(client: HydraDBClient) -> None:
    """Surgical reset: per-label range delete over the Phase 2B id space.

    HydraDB rejects label-less MATCH, and a full-label DETACH DELETE would
    also hit the Phase 1 graph — the range keeps this scoped to Phase 2B ids.
    """
    for label in ("Claim", "Artifact", "Source") + ENTITY_LABELS:
        client.execute(
            DELETE_PHASE2B.format(label=label),
            {"min_id": ID_OFFSET, "max_id": ID_OFFSET + ID_SPAN},
        )


def load_claims(
    client: HydraDBClient,
    claims: list[Claim],
    resolutions: Mapping[str, dict[str, Any]],
    fixture_artifacts: Iterable[dict[str, Any]] = (),
    fixture_sources: Iterable[dict[str, Any]] = (),
    reset: bool = False,
) -> LoadResult:
    """Validate, resolve, and write claims into HydraDB; then read back and verify."""
    entities = resolve_mentions(claims, resolutions)
    entity_keys = sorted(
        {entities[claim.subject_mention]["key"] for claim in claims}
        | {entities[claim.object_mention]["key"] for claim in claims}
    )
    entity_defs = {key: resolutions[key] for key in entity_keys}
    resolved_subjects = {claim.claim_id: entities[claim.subject_mention] for claim in claims}
    resolved_objects = {claim.claim_id: entities[claim.object_mention] for claim in claims}
    for claim in claims:
        subject = resolved_subjects[claim.claim_id]
        object_ = resolved_objects[claim.claim_id]
        if not pair_supported(claim.predicate, subject["label"], object_["label"]):
            raise ContractError(
                f"{claim.claim_id}: unsupported entity pair {claim.predicate} "
                f"({subject['label']} -> {object_['label']}); "
                f"allowed: {sorted(ENTITY_PAIR_RULES[claim.predicate])}"
            )

    claim_ids = [claim.claim_id for claim in claims]
    claim_num_ids = dict(zip(claim_ids, _next_ids(len(claim_ids), ID_OFFSET)))
    artifact_list = list(fixture_artifacts)
    source_list = list(fixture_sources)
    base = ID_OFFSET + ID_SPAN // 2
    artifact_num_ids = {a["key"]: base + index for index, a in enumerate(artifact_list)}
    source_num_ids = {s["key"]: base + len(artifact_list) + index for index, s in enumerate(source_list)}
    entity_num_ids = {
        key: base + len(artifact_list) + len(source_list) + index
        for index, key in enumerate(entity_defs)
    }

    dsid_artifacts = {row["dsid"]: row for row in client.execute(READ_DSID_ARTIFACTS).rows}
    fixture_observed = {a["key"]: a.get("observed_at") for a in artifact_list}
    claim_artifact_ids: dict[str, int] = {}
    claim_artifact_times: dict[str, str | None] = {}
    referenced_dsids: set[str] = set()
    missing_artifacts: set[str] = set()
    for claim in claims:
        artifact_id = claim.artifact_id
        if artifact_id in artifact_num_ids:
            claim_artifact_ids[claim.claim_id] = artifact_num_ids[artifact_id]
            claim_artifact_times[claim.claim_id] = fixture_observed.get(artifact_id)
        elif artifact_id in dsid_artifacts:
            claim_artifact_ids[claim.claim_id] = dsid_artifacts[artifact_id]["id"]
            claim_artifact_times[claim.claim_id] = dsid_artifacts[artifact_id].get("timestamp")
            referenced_dsids.add(artifact_id)
        else:
            missing_artifacts.add(artifact_id)
    if missing_artifacts:
        raise ContractError(
            f"claims reference {len(missing_artifacts)} artifact(s) not present in the graph: {sorted(missing_artifacts)}"
        )

    relationships = 0
    started = perf_counter()
    if reset:
        _delete_phase2b_graph(client)

    if source_list:
        client.execute_batch(
            CREATE_SOURCE_FIXTURE,
            [{"id": source_num_ids[s["key"]], "key": s["key"], "name": s["name"]} for s in source_list],
        )
        relationships += len(source_list)

    if artifact_list:
        client.execute_batch(
            CREATE_ARTIFACT_FIXTURE,
            [{"id": artifact_num_ids[a["key"]], **a, "source_id": source_num_ids[a["source_id"]]} for a in artifact_list],
        )
        relationships += len(artifact_list)

    entity_rows = [
        {
            "id": entity_num_ids[key],
            "key": key,
            "label": defn["label"],
            "name": defn["name"],
            "aliases": "|".join(defn.get("aliases", []) or []),
        }
        for key, defn in entity_defs.items()
    ]
    for label in ENTITY_LABELS:
        labeled_rows = [row for row in entity_rows if row["label"] == label]
        if labeled_rows:
            client.execute_batch(CREATE_ENTITIES.format(label=label), labeled_rows)
    relationships += len(entity_rows)

    def resolve_observed(claim: Claim) -> str:
        """Observation time for a claim: claim timestamp, else artifact timestamp.

        The graph requires an observation time (ordering/conflict resolution).
        If neither the claim nor its artifact has one, the claim is rejected —
        a temporally anonymous claim cannot enter state resolution.
        """
        value = claim.observed_at or claim_artifact_times[claim.claim_id]
        if not value:
            raise ContractError(
                f"{claim.claim_id}: no observed_at and artifact has no timestamp; "
                "temporally anonymous claims cannot enter the graph"
            )
        return value[:10]

    claim_rows = []
    for claim in claims:
        observed_at = resolve_observed(claim)
        claim_rows.append(
            {
                "id": claim_num_ids[claim.claim_id],
                "key": claim.claim_id,
                "artifact_id": claim.artifact_id,
                "subject_mention": claim.subject_mention,
                "predicate": claim.predicate,
                "object_mention": claim.object_mention,
                "subject_id": resolved_subjects[claim.claim_id]["key"],
                "subject_name": resolved_subjects[claim.claim_id]["name"],
                "object_id": resolved_objects[claim.claim_id]["key"],
                "observed_at": observed_at,
                "valid_from": (claim.valid_from or observed_at)[:10],
                "valid_to": claim.valid_to[:10] if claim.valid_to else OPEN_END,
                "confidence": claim.confidence,
                "extraction_method": claim.extraction_method,
                "evidence_span": claim.evidence_span[:200],
            }
        )
    client.execute_batch(CREATE_CLAIMS, claim_rows)

    def relate(template: str, pairs: Iterable[dict[str, Any]]) -> None:
        nonlocal relationships
        client.execute_batch(template, pairs)
        relationships += len(list(pairs))

    if artifact_list:
        relate(
            RELATE_FROM,
            [{"source": artifact_num_ids[a["key"]], "target": source_num_ids[a["source_id"]]} for a in artifact_list],
        )
    real_sources = {
        dsid_artifacts[dsid]["source"] for dsid in referenced_dsids
    }
    if real_sources:
        source_keys = sorted(f"source:{name}" for name in real_sources)
        source_extra = {
            key: ID_OFFSET + ID_SPAN - len(source_keys) + index
            for index, key in enumerate(source_keys)
        }
        client.execute_batch(
            CREATE_SOURCE_FIXTURE,
            [{"id": source_extra[key], "key": key, "name": key.removeprefix("source:")} for key in source_keys],
        )
        relationships += len(source_keys)
        real_from_rows = [
            {
                "source": dsid_artifacts[dsid]["id"],
                "target": source_extra[f"source:{dsid_artifacts[dsid]['source']}"],
            }
            for dsid in referenced_dsids
        ]
        relate(RELATE_REAL_SOURCE, real_from_rows)
    relate(
        RELATE_SOURCED_FROM,
        [{"source": claim_num_ids[c.claim_id], "target": claim_artifact_ids[c.claim_id]} for c in claims],
    )
    for olabel in ENTITY_LABELS:
        about_rows = [
            {"source": claim_num_ids[c.claim_id], "target": entity_num_ids[resolved_objects[c.claim_id]["key"]]}
            for c in claims
            if resolved_objects[c.claim_id]["label"] == olabel
        ]
        if about_rows:
            relate(RELATE_ABOUT.format(olabel=olabel), about_rows)
    for predicate in PREDICATE_RELS:
        matching = [c for c in claims if c.predicate == predicate]
        if not matching:
            continue
        for slabel in ENTITY_LABELS:
            for olabel in ENTITY_LABELS:
                rows = [
                    {
                        "source": entity_num_ids[resolved_subjects[c.claim_id]["key"]],
                        "target": entity_num_ids[resolved_objects[c.claim_id]["key"]],
                        "valid_from": (c.valid_from or resolve_observed(c))[:10],
                        "valid_to": c.valid_to[:10] if c.valid_to else OPEN_END,
                    }
                    for c in matching
                    if resolved_subjects[c.claim_id]["label"] == slabel
                    and resolved_objects[c.claim_id]["label"] == olabel
                ]
                if rows:
                    relate(RELATE_PREDICATE.format(rel=predicate, slabel=slabel, olabel=olabel), rows)
                    for row in rows:
                        client.execute(
                            SET_PREDICATE_VALIDITY.format(rel=predicate, slabel=slabel, olabel=olabel),
                            row,
                        )
    contradictions = _contradiction_pairs([{**row, "claim_id": row["key"]} for row in claim_rows])
    if contradictions:
        relate(
            RELATE_CONTRADICTS,
            [{"source": claim_num_ids[a], "target": claim_num_ids[b]} for a, b in contradictions],
        )
    load_ms = (perf_counter() - started) * 1000

    started = perf_counter()
    written = {
        row["key"]: row["id"]
        for row in client.execute(READ_ALL_CLAIMS, {"min_id": ID_OFFSET, "max_id": ID_OFFSET + ID_SPAN}).rows
    }
    read_ms = (perf_counter() - started) * 1000

    mismatches = len(claims) - len(written) if len(written) != len(claims) else 0
    return LoadResult(
        claims_attempted=len(claims),
        claims_written=len(written),
        artifacts=len(artifact_list),
        sources=len(source_list),
        entities=len(entity_rows),
        relationships=relationships,
        load_ms=load_ms,
        read_back_ms=read_ms,
        read_back_count=len(written),
        mismatches=mismatches,
    )


def read_claim(client: HydraDBClient, claim_key: str) -> dict[str, Any] | None:
    rows = client.execute(READ_CLAIM, {"key": claim_key}).rows
    return rows[0] if rows else None


def count_claims(client: HydraDBClient) -> int:
    return int(client.execute(COUNT_CLAIMS, {"min_id": ID_OFFSET, "max_id": ID_OFFSET + ID_SPAN}).rows[0]["n"])


def delete_phase2b_graph(client: HydraDBClient) -> None:
    _delete_phase2b_graph(client)
