"""JSONL IO for the shared contract: read/write claims and mentions.

The extraction pipeline writes these files; the ingestion boundary reads them.
The JSONL shape is the stable interchange format between the two subsystems.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, TextIO

from .schema import Claim, Mention
from .validate import ContractError, validate_claim, validate_mention


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ContractError(f"{path.name}:{line_number}: invalid JSON: {exc}") from exc
    return records


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def load_claims(path: Path) -> list[Claim]:
    claims = [validate_claim(record) for record in read_jsonl(path)]
    seen: set[str] = set()
    for claim in claims:
        if claim.claim_id in seen:
            raise ContractError(f"duplicate claim_id: {claim.claim_id}")
        seen.add(claim.claim_id)
    return claims


def load_mentions(path: Path) -> list[Mention]:
    mentions = [validate_mention(record) for record in read_jsonl(path)]
    seen: set[str] = set()
    for mention in mentions:
        if mention.mention_id in seen:
            raise ContractError(f"duplicate mention_id: {mention.mention_id}")
        seen.add(mention.mention_id)
    return mentions
