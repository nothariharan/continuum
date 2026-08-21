#!/usr/bin/env python3
"""Run Slack query bot in Socket Mode (dev) or process one slash payload."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC
from pathlib import Path

# Run-as-script safety: ensure repo root is importable (the extraction pipeline
# imports `scripts.checkpoint_claims` during live ingestion).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _run_socket_mode() -> int:
    try:
        from slack_bolt import App
        from slack_bolt.adapter.socket_mode import SocketModeHandler
    except ImportError:
        raise SystemExit("Install delivery deps: pip install slack-bolt")

    from datetime import datetime
    from pathlib import Path

    from continuum.delivery.slack_bot import SlackQueryBot
    from continuum.hydradb import HydraDBClient
    from continuum.pipeline.memory_worker import MemoryWorker
    from continuum.sources.events import EventQueue
    from continuum.sources.slack.models import SlackMessage
    from continuum.sources.slack.normalize import normalize_slack_message

    # Live pipeline checklist is ON in socket (demo) mode; pace it for the camera
    # with CONTINUUM_SLACK_TRACE_DELAY (seconds between checklist and answer).
    show_trace = os.environ.get("CONTINUUM_SLACK_TRACE", "1").strip().lower() in {"1", "true", "yes", "on"}
    try:
        trace_delay = float(os.environ.get("CONTINUUM_SLACK_TRACE_DELAY", "0.8") or 0)
    except ValueError:
        trace_delay = 0.8
    # Live ingest: plaintext channel messages update memory (author-ownership
    # phrasings like "I'm taking over Acme"). Requires the Slack app to subscribe
    # to `message.channels` + `channels:history`; harmless if not subscribed.
    ingest = os.environ.get("CONTINUUM_SLACK_INGEST", "1").strip().lower() in {"1", "true", "yes", "on"}

    client = HydraDBClient()
    client.health_check()
    # Force simple bot-token mode. If SLACK_CLIENT_ID/SECRET are present (they are
    # in a full .env), Bolt auto-enables OAuth/installation-store and IGNORES the
    # bot token — then every event fails with "AuthorizeResult not found" and the
    # bot never replies. Hide them so Bolt authorizes with the token directly.
    for _oauth_var in ("SLACK_CLIENT_ID", "SLACK_CLIENT_SECRET", "SLACK_INSTALLATION_STORE"):
        os.environ.pop(_oauth_var, None)
    app = App(token=os.environ["SLACK_BOT_TOKEN"])
    bot_user_id = None
    try:
        bot_user_id = app.client.auth_test().get("user_id")
    except Exception:  # non-fatal; only used to skip self/mention echoes
        bot_user_id = None
    worker = (
        MemoryWorker(client=client, queue=EventQueue(path=Path("data/ingestion/slack-events.jsonl")), lifecycle=None)
        if ingest
        else None
    )

    def _bot_for(say, thread_ts):
        def post(_channel, payload, _thread_ts):
            say(text=payload.get("text", ""), blocks=payload.get("blocks"), thread_ts=thread_ts)
        return SlackQueryBot(client, post_message=post, show_trace=show_trace, trace_delay=trace_delay)

    def _display_name(user_id):
        if not user_id:
            return None
        try:
            info = app.client.users_info(user=user_id).get("user", {})
            prof = info.get("profile", {})
            return info.get("real_name") or prof.get("display_name") or info.get("name") or user_id
        except Exception:  # noqa: BLE001 — fall back to the raw id
            return user_id

    @app.event("app_mention")
    def _mention(body, say, logger):
        event = body.get("event", {})
        thread_ts = event.get("thread_ts") or event.get("ts")
        try:
            _bot_for(say, thread_ts).handle_app_mention(event)
        except Exception as exc:
            logger.exception("mention failed")
            say(text=f"Continuum error: {exc}", thread_ts=thread_ts)

    @app.event("message")
    def _ingest_message(body, logger):
        if not worker:
            return
        event = body.get("event", {})
        # Ignore bot posts, edits/joins/etc., empty text, and questions to the bot.
        if event.get("bot_id") or event.get("subtype"):
            return
        text = (event.get("text") or "").strip()
        if not text or (bot_user_id and f"<@{bot_user_id}>" in text):
            return
        try:
            now = datetime.now(UTC)
            display = _display_name(event.get("user"))
            msg = SlackMessage(
                ts=str(event.get("ts") or f"{now.timestamp():.6f}"),
                channel_id=str(event.get("channel") or "C_LIVE"),
                channel_name=str(event.get("channel") or "live"),
                text=text,
                user_id=event.get("user"),
                user_display=display,
                username=(display or "").lower().replace(" ", "."),
            )
            artifact = normalize_slack_message(msg, ingested_at=now.isoformat())
            res = worker.ingest_artifacts([artifact])
            logger.info("ingested message author=%s claims=%s", display, res.claims_loaded)
        except Exception:  # ingestion is best-effort, never crash the bot
            logger.exception("live ingest failed")

    @app.command("/continuum")
    def _slash(ack, command, say):
        ack()
        try:
            _bot_for(say, None).handle_slash(command.get("text", ""), channel=command["channel_id"], user_id=command["user_id"])
        except Exception as exc:
            say(text=f"Continuum error: {exc}")

    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("socket", "once"), default="socket")
    parser.add_argument("--text", default="", help="Question text for --mode once")
    parser.add_argument("--channel", default="C00000000")
    args = parser.parse_args()

    # Load .env (SLACK_BOT_TOKEN / SLACK_APP_TOKEN live there) before we read them.
    from continuum.hydradb.config import _load_dotenv

    _load_dotenv()

    if args.mode == "socket":
        return _run_socket_mode()

    from continuum.delivery.slack_bot import build_bot_from_env

    # Dry-run preview: render EXACTLY what Slack will show (checklist, then answer)
    # for the given question, straight from the live canonical state.
    posts: list[dict] = []
    bot = build_bot_from_env(
        post_message=lambda _ch, payload, _ts: posts.append(payload),
        show_trace=True,
    )
    bot.handle_text(args.text, channel=args.channel)
    for i, payload in enumerate(posts):
        if i:
            print("---")
        print(payload.get("text", "").encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
