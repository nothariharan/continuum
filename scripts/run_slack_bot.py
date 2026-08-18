#!/usr/bin/env python3
"""Run Slack query bot in Socket Mode (dev) or process one slash payload."""

from __future__ import annotations

import argparse
import json
import os
import sys


def _run_socket_mode() -> int:
    try:
        from slack_bolt import App
        from slack_bolt.adapter.socket_mode import SocketModeHandler
    except ImportError:
        raise SystemExit("Install delivery deps: pip install slack-bolt")

    from continuum.delivery.slack_bot import build_bot_from_env

    bot = build_bot_from_env()
    app = App(token=os.environ["SLACK_BOT_TOKEN"])

    @app.event("app_mention")
    def _mention(body, say, logger):
        event = body.get("event", {})
        try:
            payload = bot.handle_app_mention(event)
            say(text=payload.get("text", ""), blocks=payload.get("blocks"))
        except Exception as exc:
            logger.exception("mention failed")
            say(text=f"Continuum error: {exc}")

    @app.command("/continuum")
    def _slash(ack, command, say):
        ack()
        try:
            payload = bot.handle_slash(command.get("text", ""), channel=command["channel_id"], user_id=command["user_id"])
            say(text=payload.get("text", ""), blocks=payload.get("blocks"))
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

    bot = build_bot_from_env()
    payload = bot.handle_text(args.text, channel=args.channel)
    json.dump(payload, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
