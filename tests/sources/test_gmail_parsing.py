"""Gmail MIME body extraction + quoted-history splitting (Sections 4)."""

from __future__ import annotations

import base64

from continuum.sources.gmail.models import GmailMessage
from continuum.sources.gmail.normalize import normalize_gmail_message, split_new_and_quoted


def _b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def test_multipart_prefers_text_plain():
    message = {
        "id": "mp1",
        "threadId": "t",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [{"name": "From", "value": "a@x.com"}, {"name": "Subject", "value": "S"}],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _b64url("plain wins")}},
                {"mimeType": "text/html", "body": {"data": _b64url("<p>html loses</p>")}},
            ],
        },
    }
    msg = GmailMessage.from_api_message(message)
    assert msg.body == "plain wins"


def test_html_fallback_when_no_plain():
    message = {
        "id": "h1",
        "threadId": "t",
        "payload": {
            "mimeType": "text/html",
            "headers": [{"name": "From", "value": "a@x.com"}],
            "body": {"data": _b64url("<p>Hello <b>world</b></p>")},
        },
    }
    msg = GmailMessage.from_api_message(message)
    assert "Hello" in msg.body and "world" in msg.body
    assert "<p>" not in msg.body


def test_attachment_filenames_extracted():
    message = {
        "id": "a1",
        "threadId": "t",
        "payload": {
            "mimeType": "multipart/mixed",
            "headers": [{"name": "From", "value": "a@x.com"}],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _b64url("see attached")}},
                {"mimeType": "application/pdf", "filename": "contract.pdf", "body": {"attachmentId": "z"}},
            ],
        },
    }
    msg = GmailMessage.from_api_message(message)
    assert msg.attachments == ["contract.pdf"]


def test_split_quoted_on_angle_bracket():
    body = "New decision: Priya owns Acme.\n> On Jul 1 Morgan wrote:\n> I own Acme."
    new, quoted = split_new_and_quoted(body)
    assert new == "New decision: Priya owns Acme."
    assert "Morgan wrote" in quoted


def test_split_quoted_on_on_wrote_marker():
    body = "Confirming the handoff.\nOn Mon, Jul 1, 2026 Morgan <m@x.com> wrote:\nOld content here."
    new, quoted = split_new_and_quoted(body)
    assert new == "Confirming the handoff."
    assert "Old content here" in quoted


def test_no_quote_returns_full_body():
    body = "Just a plain message with no quoting."
    new, quoted = split_new_and_quoted(body)
    assert new == body
    assert quoted == ""


def test_quoted_history_kept_out_of_content_but_in_metadata():
    message = {
        "id": "q1",
        "threadId": "t",
        "payload": {
            "mimeType": "text/plain",
            "headers": [{"name": "From", "value": "priya@company.com"}, {"name": "Subject", "value": "Handoff"}],
            "body": {"data": _b64url("Priya owns Acme now.\n> Morgan owned Acme before.")},
        },
    }
    artifact = normalize_gmail_message(GmailMessage.from_api_message(message))
    assert "Priya owns Acme now" in artifact.content
    assert "Morgan owned Acme before" not in artifact.content
    assert artifact.metadata["has_quoted_history"] is True
    assert "Morgan owned Acme before" in artifact.metadata["quoted_excerpt"]
