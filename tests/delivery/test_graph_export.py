"""Tests for read-only graph export."""

from __future__ import annotations

from continuum.delivery.graph_export import export_entity_graph


def test_export_entity_graph_empty_client_shape():
    class FakeClient:
        def execute(self, *_args, **_kwargs):
            class Result:
                rows = []

            return Result()

    payload = export_entity_graph(FakeClient(), "account:acme")
    assert payload["entity"] == "account:acme"
    assert payload["nodes"]
    assert payload["edges"] == []
