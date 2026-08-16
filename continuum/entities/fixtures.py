"""Phase 3 — tiny manually-labeled entity-resolution fixture.

Represents the canonical hard case from the AGENTS.md identity preview:

    "Sam"                       (first-name mention)
    "@soham"                    (username)
    "S. Ratnaparkhi"            (initialized name)
    "soham-dev"                 (dev username)
    "soham@company.com"         (email)

All five are the same person (Soham Ratnaparkhi). Also includes two
hard-negative families to exercise KEEP_SEPARATE:
    Maya Chen  vs  Maya Patel     (same first name, different people)
    Sarah Chen vs Sarah Liu       (same first name, different people)

Expected verdicts:
    (soham cluster)        -> person:soham-ratnaparkhi
    (maya chen / maya patel) -> KEEP_SEPARATE
    (sarah chen / sarah liu)  -> KEEP_SEPARATE
"""

from __future__ import annotations

import json
from pathlib import Path

from continuum.entities.candidates import candidate_from_mention
from continuum.entities.models import CanonicalEntity, EntityCandidate

FIXTURE = [
    {"mention": "Sam", "type": "person", "usernames": [], "emails": []},
    {"mention": "@soham", "type": "person", "usernames": ["soham"], "emails": []},
    {"mention": "S. Ratnaparkhi", "type": "person", "usernames": [], "emails": []},
    {"mention": "soham-dev", "type": "person", "usernames": ["soham-dev"], "emails": []},
    {"mention": "soham@company.com", "type": "email", "usernames": [], "emails": ["soham@company.com"]},
    {"mention": "Maya Chen", "type": "person", "usernames": [], "emails": ["maya.chen@redwood.com"]},
    {"mention": "Maya Patel", "type": "person", "usernames": [], "emails": ["maya.patel@redwood.com"]},
    {"mention": "Sarah Chen", "type": "person", "usernames": ["sarah_csm"], "emails": ["sarah.chen@redwood.com"]},
    {"mention": "Sarah Liu", "type": "person", "usernames": [], "emails": ["sarah.liu@cloudpartner.com"]},
]

EXPECTED_MERGED = {
    "soham": {"person:sam", "person:soham", "person:s-ratnaparkhi", "person:soham-dev", "email:soham-company-com"},
}

EXPECTED_SEPARATE = [
    ("Maya Chen", "Maya Patel"),
    ("Sarah Chen", "Sarah Liu"),
]


def load_candidates(path: Path | None = None) -> list[EntityCandidate]:
    path = path or Path(__file__).resolve().parents[2] / "data" / "fixtures" / "phase3" / "identity-fixture.json"
    if path.exists():
        rows = json.loads(path.read_text(encoding="utf-8"))
    else:
        rows = FIXTURE
    return [candidate_from_mention(**row) for row in rows]


def load_lexicon() -> list[CanonicalEntity]:
    """Known-good canonical entities from the real-claims fixture (subset)."""
    return [
        CanonicalEntity(
            entity_key="person:may-patel",
            label="Person",
            name="Maya Patel",
            aliases={"Maya", "Maya Patel"},
            emails={"maya.patel@redwood.com"},
        ),
        CanonicalEntity(
            entity_key="person:may-chen",
            label="Person",
            name="Maya Chen",
            aliases={"Maya Chen"},
            emails={"maya.chen@redwood.com"},
        ),
        CanonicalEntity(
            entity_key="person:sarah-chen",
            label="Person",
            name="Sarah Chen",
            aliases={"sarah_csm"},
            emails={"sarah.chen@redwood.com"},
        ),
    ]


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "phase3" / "identity-fixture.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(FIXTURE, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(FIXTURE)} fixture mentions -> {out}")
