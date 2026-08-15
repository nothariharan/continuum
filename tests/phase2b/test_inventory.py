"""Mention inventory tests."""

from continuum.extract.inventory import build_mention_inventory
from continuum.extract.schemas import Mention


def test_inventory_cross_source_overlap():
    mentions = [
        Mention.create(
            artifact_id="dsid_a",
            source="slack",
            raw_text="Sarah Chen",
            type="person",
            content="Sarah Chen owns Acme",
            span_start=0,
            span_end=10,
        ),
        Mention.create(
            artifact_id="dsid_b",
            source="gmail",
            raw_text="Sarah Chen",
            type="person",
            content="From Sarah Chen",
            span_start=5,
            span_end=15,
            source_identity="sarah@example.com",
        ),
        Mention.create(
            artifact_id="dsid_c",
            source="linear",
            raw_text="S Chen",
            type="person",
            content="Assigned S Chen",
            span_start=9,
            span_end=15,
        ),
    ]
    inventory = build_mention_inventory(mentions)
    sarah = next(e for e in inventory if e["normalized"] == "sarah chen")
    assert sarah["frequency"] == 2
    assert set(sarah["sources"]) == {"slack", "gmail"}
