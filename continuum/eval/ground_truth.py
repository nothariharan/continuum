"""Ground-truth loading for Phase 2B extraction evaluation."""

from __future__ import annotations

from pathlib import Path

from continuum.extract.schemas import GroundTruthRecord, read_jsonl


def load_ground_truth(path: Path) -> list[GroundTruthRecord]:
    records: list[GroundTruthRecord] = []
    for row in read_jsonl(path):
        records.append(
            GroundTruthRecord(
                artifact_id=row["artifact_id"],
                mentions=row.get("mentions", []),
                claims=row.get("claims", []),
                notes=row.get("notes", ""),
            )
        )
    return records


def ground_truth_by_artifact(records: list[GroundTruthRecord]) -> dict[str, GroundTruthRecord]:
    return {record.artifact_id: record for record in records}
