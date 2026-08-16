"""Precision/recall metrics for mention and claim extraction."""

from __future__ import annotations

from continuum.eval.gold_v1 import GoldBenchmark, GoldClaimRow
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


def gold_claim_key(row: GoldClaimRow | dict) -> tuple[str, str, str]:
    if isinstance(row, GoldClaimRow):
        return _claim_key(row.subject, row.predicate, row.object)
    return _claim_key(row["subject"], row["predicate"], row["object"])


def gold_mention_rows(benchmark: GoldBenchmark) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for mention in benchmark.mentions:
        grouped.setdefault(mention.artifact_id, []).append(
            {
                "raw_text": mention.raw_text,
                "type": mention.type,
                "source_identity": mention.source_identity,
            }
        )
    return grouped


def score_gold_mentions(
    predicted: list[Mention],
    benchmark: GoldBenchmark,
) -> dict[str, float | int]:
    rows = []
    gold_by_artifact = gold_mention_rows(benchmark)
    for artifact_id, gold_rows in gold_by_artifact.items():
        if not gold_rows:
            continue
        pred = [m for m in predicted if m.artifact_id == artifact_id]
        rows.append(score_mentions(pred, gold_rows, artifact_id=artifact_id))
    return aggregate_scores(rows)


def score_gold_claims_strict(
    predicted: list[Claim],
    benchmark: GoldBenchmark,
) -> dict[str, float | int]:
    """Precision/recall on VALID gold claims only (legacy-compatible)."""
    rows = []
    valid_by_artifact = benchmark.claims_by_artifact()
    for artifact_id, gold_rows in valid_by_artifact.items():
        gold_dicts = [
            {
                "subject_mention": row.subject,
                "predicate": row.predicate,
                "object_mention": row.object,
            }
            for row in gold_rows
        ]
        pred = [c for c in predicted if c.artifact_id == artifact_id]
        rows.append(score_claims(pred, gold_dicts, artifact_id=artifact_id))
    return aggregate_scores(rows)


def score_gold_claims_abstention(
    predicted: list[Claim],
    benchmark: GoldBenchmark,
) -> dict[str, float | int]:
    """Abstention-aware claim scoring across all gold artifacts."""
    tp = fp = fn = tn = 0
    ambiguous_artifacts = 0

    for artifact_id in sorted(benchmark.artifact_ids):
        expectation = benchmark.artifact_claim_expectation(artifact_id)
        pred = [c for c in predicted if c.artifact_id == artifact_id]
        pred_keys = {_claim_key(c.subject_mention, c.predicate, c.object_mention) for c in pred}

        if expectation == "AMBIGUOUS":
            ambiguous_artifacts += 1
            continue

        valid_gold = [
            gold_claim_key(row)
            for row in benchmark.claims
            if row.artifact_id == artifact_id and row.status == "VALID"
        ]
        gold_set = set(valid_gold)

        if expectation == "NO_CLAIM":
            if pred_keys:
                fp += len(pred_keys)
            else:
                tn += 1
            continue

        tp += len(gold_set & pred_keys)
        fp += len(pred_keys - gold_set)
        fn += len(gold_set - pred_keys)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    abstention_precision = tn / (tn + fp) if (tn + fp) else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "abstention_precision": round(abstention_precision, 4),
        "ambiguous_artifacts_excluded": ambiguous_artifacts,
    }


def score_gold_claims_by_predicate(
    predicted: list[Claim],
    benchmark: GoldBenchmark,
) -> dict[str, dict[str, float | int]]:
    by_predicate: dict[str, list[dict[str, float | int]]] = {}
    valid_by_artifact = benchmark.claims_by_artifact()
    for artifact_id, gold_rows in valid_by_artifact.items():
        pred = [c for c in predicted if c.artifact_id == artifact_id]
        for row in gold_rows:
            gold_dict = {
                "subject_mention": row.subject,
                "predicate": row.predicate,
                "object_mention": row.object,
            }
            scores = score_claims(
                [c for c in pred if c.predicate == row.predicate],
                [gold_dict],
                artifact_id=artifact_id,
            )
            by_predicate.setdefault(row.predicate, []).append(scores)
    return {predicate: aggregate_scores(rows) for predicate, rows in sorted(by_predicate.items())}
