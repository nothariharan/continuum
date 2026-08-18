"""B2 regression tests — effective-date validity (PR #10 review failures).

Lock:
- 'effective July 28' / 'from July 28' populate valid_from / valid_to
- year resolution is deterministic and never guesses
- state resolution answers as-of queries from validity, not observation time

Review failures this locks:
- se2e-11 "When did Camila become owner?" returned 2024-10-07 (artifact ts)
  instead of 2026-07-28 (effective date)
- se2e-16 "as of 2026-07-27" returned Camila instead of Maya
"""

from __future__ import annotations

from continuum.pipeline.source_e2e import (
    _claim_validity,
    _collect_effective_anchors,
    _effective_dates,
    _resolve_effective_year,
)
from continuum.sources.gmail.models import GmailMessage
from continuum.sources.gmail.normalize import normalize_gmail_message

# ---------------------------------------------------------------------------
# Effective-date parsing
# ---------------------------------------------------------------------------


def test_effective_from_july():
    anchor = {"cedarbank": 2026}
    effective, until = _effective_dates(
        "taking over CedarBank ownership from July 28", "2024-10-07", "CedarBank", anchor
    )
    assert effective == "2026-07-28"
    assert until is None


def test_effective_july_with_explicit_year():
    anchor = {}
    effective, _ = _effective_dates(
        "handing off CedarBank account ownership to you effective July 28, 2027",
        "2027-07-27", "CedarBank", anchor,
    )
    assert effective == "2027-07-28"


def test_effective_same_year_when_near_observed():
    anchor = {}
    effective, _ = _effective_dates(
        "handing off CedarBank account ownership to you effective July 28",
        "2026-07-27", "CedarBank", anchor,
    )
    assert effective == "2026-07-28"


def test_effective_abstains_when_year_ambiguous():
    # July 28 is far in the past relative to an October observation and no
    # cross-artifact anchor exists — never guess.
    effective, _ = _effective_dates(
        "taking over CedarBank ownership from July 28", "2024-10-07", "CedarBank", {}
    )
    assert effective is None


def test_until_date():
    anchor = {}
    _, until = _effective_dates(
        "I still own CedarBank until September 30", "2026-09-01", "CedarBank", anchor
    )
    assert until == "2026-09-30"


def test_effective_year_resolution_rules():
    assert _resolve_effective_year(7, 28, 2027, "2026-07-27", "cedarbank", {}) == "2027-07-28"
    assert _resolve_effective_year(7, 28, None, "2026-07-27", "cedarbank", {}) == "2026-07-28"
    assert _resolve_effective_year(7, 28, None, "2024-10-07", "cedarbank", {"cedarbank": 2026}) == "2026-07-28"
    assert _resolve_effective_year(7, 28, None, "2024-10-07", "cedarbank", {}) is None


def test_claim_validity_verb_semantics():
    assert _claim_validity("taking over CedarBank ownership", "2026-07-28", None) == ("2026-07-28", None)
    assert _claim_validity("handing off CedarBank account ownership", "2026-07-28", None) == (None, "2026-07-28")
    assert _claim_validity("I still own CedarBank", None, "2026-09-30") == (None, "2026-09-30")
    assert _claim_validity("Morgan owns Acme", "2026-07-28", None) == ("2026-07-28", None)


def test_anchor_collection_from_artifacts():
    message = GmailMessage.from_rfc822_text(
        message_id="m1",
        thread_id="t1",
        text=(
            "From: Maya Patel <maya.patel@redwood.com>\n"
            "To: Camila Reyes <camila.reyes@redwood.com>\n"
            "Date: 2026-07-27T10:00:00Z\n"
            "Subject: CedarBank handoff\n\n"
            "Confirming I am handing off CedarBank account ownership to you effective July 28."
        ),
    )
    artifact = normalize_gmail_message(message)
    anchors = _collect_effective_anchors([artifact])
    assert anchors == {"cedarbank": 2026}
