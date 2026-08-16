"""Entity-resolution evaluation harness — the resolver's acceptance gate.

Consumes identity-pairs.jsonl (gold labels) + the resolver's decisions and
reports the metrics that decide whether the resolver may touch the graph:

    pair accuracy          exact label match rate
    SAME precision/recall  MERGE found for SAME pairs
    DIFFERENT precision/recall  KEEP_SEPARATE for DIFFERENT pairs
    false merge rate       MERGE on a DIFFERENT/UNCERTAIN pair  <-- CRITICAL
    false split rate       KEEP_SEPARATE on a SAME pair
    review rate            REVIEW decisions
    abstain rate           ABSTAIN decisions
    decision distribution  MERGE/KEEP_SEPARATE/REVIEW/ABSTAIN counts

Decision mapping (conservative):
    gold SAME_ENTITY       -> expected MERGE
    gold DIFFERENT_ENTITY  -> expected KEEP_SEPARATE (REVIEW/ABSTAIN are
                             safe misses, not false splits)
    gold UNCERTAIN         -> expected REVIEW or ABSTAIN; MERGE here counts
                             as a false merge (never guess)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import ResolutionDecision, ResolutionVerdict
from .pairs import IdentityPair
from .resolver import EntityResolver

GOLD_TO_DECISION = {
    "SAME_ENTITY": ResolutionDecision.MERGE,
    "DIFFERENT_ENTITY": ResolutionDecision.KEEP_SEPARATE,
    "UNCERTAIN": None,  # REVIEW or ABSTAIN both acceptable
}


@dataclass
class PairEvalRow:
    pair_id: str
    gold: str
    decision: ResolutionDecision
    score: float
    signals: tuple[str, ...]
    correct: bool
    false_merge: bool = False
    false_split: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "gold": self.gold,
            "decision": self.decision.value,
            "score": round(self.score, 4),
            "signals": list(self.signals),
            "correct": self.correct,
            "false_merge": self.false_merge,
            "false_split": self.false_split,
            "notes": self.notes,
        }


@dataclass
class EntityResolutionEval:
    pairs: list[IdentityPair]
    rows: list[PairEvalRow] = field(default_factory=list)

    def run(self, resolver: EntityResolver | None = None) -> dict[str, Any]:
        resolver = resolver or EntityResolver()
        self.rows = []
        for pair in self.pairs:
            verdict = self._resolve_pair(resolver, pair)
            self.rows.append(self._classify(pair, verdict))
        return self.summary()

    def _resolve_pair(self, resolver: EntityResolver, pair: IdentityPair) -> ResolutionVerdict:
        return resolver.resolve_pair(
            pair.candidate_a(),
            pair.candidate_b(),
            features=pair.merged_features(),
        )

    def _classify(self, pair: IdentityPair, verdict: ResolutionVerdict) -> PairEvalRow:
        gold = pair.label
        decision = verdict.decision
        expected = GOLD_TO_DECISION[gold]

        if gold == "SAME_ENTITY":
            correct = decision == ResolutionDecision.MERGE
            false_split = decision == ResolutionDecision.KEEP_SEPARATE
            false_merge = False
        elif gold == "DIFFERENT_ENTITY":
            correct = decision == ResolutionDecision.KEEP_SEPARATE
            false_merge = decision == ResolutionDecision.MERGE
            false_split = False
        else:  # UNCERTAIN
            correct = decision in {ResolutionDecision.REVIEW, ResolutionDecision.ABSTAIN}
            false_merge = decision == ResolutionDecision.MERGE
            false_split = decision == ResolutionDecision.KEEP_SEPARATE

        return PairEvalRow(
            pair_id=pair.pair_id,
            gold=gold,
            decision=decision,
            score=verdict.score,
            signals=verdict.signals,
            correct=correct,
            false_merge=false_merge,
            false_split=false_split,
            notes=verdict.reason[:160],
        )

    def summary(self) -> dict[str, Any]:
        if not self.rows:
            return {"pairs": 0, "metrics": {}}

        total = len(self.rows)
        same = [r for r in self.rows if r.gold == "SAME_ENTITY"]
        diff = [r for r in self.rows if r.gold == "DIFFERENT_ENTITY"]
        unc = [r for r in self.rows if r.gold == "UNCERTAIN"]

        def prf(group: list[PairEvalRow], *, decision: ResolutionDecision, positive: bool) -> dict[str, float]:
            """Precision/recall for a gold class.

            For SAME: positive = MERGE decisions; a row is a TP when
            correct (gold SAME and decided MERGE).
            For DIFFERENT: positive = KEEP_SEPARATE decisions.
            """
            tp = sum(1 for r in group if r.correct)
            fn = sum(1 for r in group if not r.correct)
            fp = sum(
                1
                for r in self.rows
                if r.decision == decision and r.gold != ("SAME_ENTITY" if positive else "DIFFERENT_ENTITY")
            )
            precision = tp / (tp + fp) if (tp + fp) else 0.0
            recall = tp / len(group) if group else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
            return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}

        from collections import Counter

        decision_dist = Counter(r.decision.value for r in self.rows)

        # False-merge rate: MERGE decisions on non-SAME gold / all MERGE decisions.
        merges = [r for r in self.rows if r.decision == ResolutionDecision.MERGE]
        false_merges = [r for r in merges if r.false_merge or r.gold != "SAME_ENTITY"]
        false_merge_rate = len(false_merges) / len(merges) if merges else 0.0

        false_splits = [r for r in self.rows if r.false_split]
        false_split_rate = len(false_splits) / len(same) if same else 0.0

        correct = sum(1 for r in self.rows if r.correct)

        same_m = prf(same, decision=ResolutionDecision.MERGE, positive=True)
        diff_m = prf(diff, decision=ResolutionDecision.KEEP_SEPARATE, positive=False)

        return {
            "pairs": total,
            "metrics": {
                "pair_accuracy": round(correct / total, 4),
                "same_precision": same_m["precision"],
                "same_recall": same_m["recall"],
                "same_f1": same_m["f1"],
                "different_precision": diff_m["precision"],
                "different_recall": diff_m["recall"],
                "different_f1": diff_m["f1"],
                "false_merge_rate": round(false_merge_rate, 4),
                "false_merge_count": len(false_merges),
                "false_split_rate": round(false_split_rate, 4),
                "false_split_count": len(false_splits),
                "review_rate": round(decision_dist.get("REVIEW", 0) / total, 4),
                "abstain_rate": round(decision_dist.get("ABSTAIN", 0) / total, 4),
                "review_count": decision_dist.get("REVIEW", 0),
                "abstain_count": decision_dist.get("ABSTAIN", 0),
            },
            "decision_distribution": dict(decision_dist),
            "gold_distribution": dict(Counter(r.gold for r in self.rows)),
            "rows": [r.to_dict() for r in self.rows],
        }


def evaluate_pairs(pairs: list[IdentityPair], resolver: EntityResolver | None = None) -> dict[str, Any]:
    return EntityResolutionEval(pairs).run(resolver)
