"""Phase 2B extraction evaluation."""

from .experiment import run_extraction_eval
from .failures import FAILURE_CATEGORIES, build_failure_corpus
from .gold_v1 import (
    GoldBenchmark,
    build_gold_benchmark,
    load_gold_benchmark,
    validate_gold_benchmark,
    write_gold_benchmark,
)
from .ground_truth import ground_truth_by_artifact, load_ground_truth
from .metrics import (
    aggregate_scores,
    score_by_predicate,
    score_claims,
    score_gold_claims_abstention,
    score_gold_claims_by_predicate,
    score_gold_claims_strict,
    score_gold_mentions,
    score_mentions,
)

__all__ = [
    "FAILURE_CATEGORIES",
    "GoldBenchmark",
    "aggregate_scores",
    "build_failure_corpus",
    "build_gold_benchmark",
    "ground_truth_by_artifact",
    "load_ground_truth",
    "load_gold_benchmark",
    "run_extraction_eval",
    "score_by_predicate",
    "score_claims",
    "score_gold_claims_abstention",
    "score_gold_claims_by_predicate",
    "score_gold_claims_strict",
    "score_gold_mentions",
    "score_mentions",
    "validate_gold_benchmark",
    "write_gold_benchmark",
]
