"""Shared provenance helpers for source adapters."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slack_permalink(workspace: str, channel_id: str, message_ts: str) -> str:
    ts_no_dot = message_ts.replace(".", "")
    return f"https://{workspace}.slack.com/archives/{channel_id}/p{ts_no_dot}"


def gmail_source_url(message_id: str) -> str:
    return f"https://mail.google.com/mail/u/0/#inbox/{message_id}"


def github_source_url(repo: str, kind: str, number: int) -> str:
    if kind == "pull_request":
        return f"https://github.com/{repo}/pull/{number}"
    return f"https://github.com/{repo}/issues/{number}"


def jira_source_url(base_url: str, issue_key: str) -> str:
    base = base_url.rstrip("/")
    return f"{base}/browse/{issue_key}"
