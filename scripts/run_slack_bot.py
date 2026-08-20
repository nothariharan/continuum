#!/usr/bin/env python3
"""Run Slack query bot in Socket Mode (dev) or process one slash payload."""

from __future__ import annotations

import argparse
import os


def _run_socket_mode() -> int:
    try:
        from slack_bolt import App
        from slack_bolt.adapter.socket_mode import SocketModeHandler
    except ImportError:
        raise SystemExit("Install delivery deps: pip install slack-bolt")

    from continuum.delivery.slack_bot import SlackQueryBot
    from continuum.hydradb import HydraDBClient

    # Live pipeline checklist is ON in socket (demo) mode; pace it for the camera
    # with CONTINUUM_SLACK_TRACE_DELAY (seconds between checklist and answer).
    show_trace = os.environ.get("CONTINUUM_SLACK_TRACE", "1").strip().lower() in {"1", "true", "yes", "on"}
    try:
        trace_delay = float(os.environ.get("CONTINUUM_SLACK_TRACE_DELAY", "0.8") or 0)
    except ValueError:
        trace_delay = 0.8

    client = HydraDBClient()
    client.health_check()
    app = App(token=os.environ["SLACK_BOT_TOKEN"])

    def _bot_for(say, thread_ts):
        def post(_channel, payload, _thread_ts):
            say(text=payload.get("text", ""), blocks=payload.get("blocks"), thread_ts=thread_ts)
        return SlackQueryBot(client, post_message=post, show_trace=show_trace, trace_delay=trace_delay)

    @app.event("app_mention")
    def _mention(body, say, logger):
        event = body.get("event", {})
        thread_ts = event.get("thread_ts") or event.get("ts")
        try:
            _bot_for(say, thread_ts).handle_app_mention(event)
        except Exception as exc:
            logger.exception("mention failed")
            say(text=f"Continuum error: {exc}", thread_ts=thread_ts)

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
