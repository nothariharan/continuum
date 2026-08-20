"""Slack query bot handlers — slash command and app_mention."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from continuum.delivery.query_service import QueryService
from continuum.delivery.slack_formatter import format_slack_answer, format_slack_trace
from continuum.hydradb import HydraDBClient

_MENTION_RE = re.compile(r"<@[A-Z0-9]+>\s*", re.IGNORECASE)


def extract_question(text: str) -> str:
    return _MENTION_RE.sub("", text).strip()


class SlackQueryBot:
    """Handle Slack queries via QueryService — no duplicated reasoning."""

    def __init__(
        self,
        client: HydraDBClient,
        *,
        entity_store=None,
        post_message: Callable[[str, dict[str, Any], str | None], None] | None = None,
        show_trace: bool = False,
        trace_delay: float = 0.0,
    ) -> None:
        self._client = client
        self._entity_store = entity_store
        self._post = post_message or self._default_post_message
        # When enabled, post the live pipeline checklist before the answer — used
        # for the demo/recording. Off by default so programmatic callers get one
        # answer message.
        self._show_trace = show_trace
        self._trace_delay = trace_delay

    def _service(self) -> QueryService:
        return QueryService(self._client, entity_store=self._entity_store)

    def handle_text(self, text: str, *, channel: str, thread_ts: str | None = None) -> dict[str, Any]:
        question = extract_question(text)
        if not question:
            payload = {"text": "Ask a question, e.g. `@continuum who owns Acme?`"}
            self._post(channel, payload, thread_ts)
            return payload
        result = self._service().ask(question)
        self._enrich_history(result)
        if self._show_trace:
            self._post(channel, format_slack_trace(result), thread_ts)
            if self._trace_delay > 0:
                time.sleep(self._trace_delay)
        payload = format_slack_answer(result)
        self._post(channel, payload, thread_ts)
        return payload

    def _enrich_history(self, result: dict[str, Any]) -> None:
        """Attach the ownership timeline so the answer can show 'Previously: …'.

        The current-state envelope only carries the active interval (empty
        history); we fetch the canonical history for the same entity/predicate so
        the reply names the prior owner. Best-effort — never blocks the answer.
        """
        state = result.get("state_result") or {}
        if state.get("status") != "definitive" or state.get("resolution") == "before":
            return
        if state.get("history") or not (state.get("value") or {}).get("name"):
            return
        entity_id = state.get("entity_id")
        if not entity_id:
            return
        try:
            from continuum.entities.store import EntityStore
            from continuum.query.semantic import StateQueryAdapter

            store = self._entity_store or EntityStore(self._client)
            hist = StateQueryAdapter(self._client, entity_store=store).get_history(
                str(entity_id), str(state.get("predicate") or "OWNS")
            )
            rows = hist.get("history") or []
            if rows:
                state["history"] = rows
        except Exception:  # noqa: BLE001 — enrichment is optional, answer stands without it
            pass

    def handle_slash(self, text: str, *, channel: str, user_id: str) -> dict[str, Any]:
        return self.handle_text(text or "", channel=channel, thread_ts=None)

    def handle_app_mention(self, event: dict[str, Any]) -> dict[str, Any]:
        return self.handle_text(
            str(event.get("text") or ""),
            channel=str(event.get("channel")),
            thread_ts=event.get("thread_ts") or event.get("ts"),
        )

    @staticmethod
    def _default_post_message(channel: str, payload: dict[str, Any], thread_ts: str | None) -> None:
        token = os.environ.get("SLACK_BOT_TOKEN")
        if not token:
            raise RuntimeError("SLACK_BOT_TOKEN required to post messages")
        body: dict[str, Any] = {"channel": channel, **payload}
        if thread_ts:
            body["thread_ts"] = thread_ts
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Slack post failed: {exc}") from exc
        if not result.get("ok"):
            raise RuntimeError(f"Slack post failed: {result.get('error')}")


def build_bot_from_env(
    post_message: Callable[[str, dict[str, Any], str | None], None] | None = None,
    *,
    show_trace: bool | None = None,
    trace_delay: float | None = None,
) -> SlackQueryBot:
    client = HydraDBClient()
    client.health_check()
    if show_trace is None:
        show_trace = os.environ.get("CONTINUUM_SLACK_TRACE", "").strip().lower() in {"1", "true", "yes", "on"}
    if trace_delay is None:
        try:
            trace_delay = float(os.environ.get("CONTINUUM_SLACK_TRACE_DELAY", "0") or 0)
        except ValueError:
            trace_delay = 0.0
    return SlackQueryBot(client, post_message=post_message, show_trace=show_trace, trace_delay=trace_delay)
