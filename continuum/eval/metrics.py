"""Precision/recall metrics for mention and claim extraction."""

from __future__ import annotations

from continuum.extract.schemas import Claim, Mention, normalize_mention_text


def _mention_key(raw_text: str, type_: str) -> tuple[str, str]:
    return (normalize_mention_text(raw_text), type_)


def _claim_key(subject: str, predicate: str, obj: str) -> tuple[str, str, str]:
    return (
        normalize_mention_text(subject),
        predicate.upper(),
        normalize_mention_text(obj),
    )


def score_mentions(
    predicted: list[Mention],
    gold_rows: list[dict],
    *,
    artifact_id: str | None = None,
) -> dict[str, float]:
    gold = {
        _mention_key(row["raw_text"], row["type"])
        for row in gold_rows
    }
    pred = {
        _mention_key(m.raw_text, m.type)
        for m in predicted
        if artifact_id is None or m.artifact_id == artifact_id
    }
    return _prf(gold, pred)


def score_claims(
    predicted: list[Claim],
    gold_rows: list[dict],
    *,
    artifact_id: str | None = None,
) -> dict[str, float]:
    gold = {
        _claim_key(row["subject_mention"], row["predicate"], row["object_mention"])
        for row in gold_rows
    }
    pred = {
        _claim_key(c.subject_mention, c.predicate, c.object_mention)
        for c in predicted
        if artifact_id is None or c.artifact_id == artifact_id
    }
    return _prf(gold, pred)


def _prf(gold: set, pred: set) -> dict[str, float]:
    tp = len(gold & pred)
    fp = len(pred - gold)
    fn = len(gold - pred)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def aggregate_scores(rows: list[dict[str, float]]) -> dict[str, float]:
    if not rows:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "tp": 0, "fp": 0, "fn": 0}
    tp = sum(r["tp"] for r in rows)
    fp = sum(r["fp"] for r in rows)
    fn = sum(r["fn"] for r in rows)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def score_by_predicate(claims: list[Claim], gold_records: list[dict]) -> dict[str, dict]:
    by_predicate: dict[str, dict] = {}
    gold_by_artifact = {row["artifact_id"]: row for row in gold_records}
    predicates = sorted({c.predicate for c in claims} | {g["predicate"] for r in gold_records for g in r.get("claims", [])})
    for predicate in predicates:
        rows = []
        for artifact_id, gold in gold_by_artifact.items():
            gold_rows = [g for g in gold.get("claims", []) if g["predicate"] == predicate]
            if not gold_rows:
                continue
            pred = [c for c in claims if c.artifact_id == artifact_id and c.predicate == predicate]
            rows.append(score_claims(pred, gold_rows, artifact_id=artifact_id))
        by_predicate[predicate] = aggregate_scores(rows)
    return by_predicate
