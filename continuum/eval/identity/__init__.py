"""Identity-pair gold dataset v1 — schema, candidates, features, report."""

from .candidates import build_identity_pairs_v1
from .features import attach_features, load_artifact_index
from .report import build_identity_pairs_report, write_identity_pairs_report
from .schema import (
    DATASET_VERSION,
    FEATURE_SLOTS,
    IDENTITY_LABELS,
    IdentityPairRow,
    load_identity_pairs,
    validate_identity_pair,
    validate_identity_pairs,
    write_identity_pairs,
)

__all__ = [
    "DATASET_VERSION",
    "FEATURE_SLOTS",
    "IDENTITY_LABELS",
    "IdentityPairRow",
    "attach_features",
    "build_identity_pairs_report",
    "build_identity_pairs_v1",
    "load_artifact_index",
    "load_identity_pairs",
    "validate_identity_pair",
    "validate_identity_pairs",
    "write_identity_pairs",
    "write_identity_pairs_report",
]
