#!/usr/bin/env python3
"""Run Slack Events API gateway for ingestion (ACK fast)."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from continuum.sources.events import EventQueue, SourceEvent
from continuum.sources.provenance import utc_now_iso
from continuum.sources.slack.events import SlackEventsGateway


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--queue", default="data/ingestion/slack-events.jsonl")
    args = parser.parse_args()

    import os

    secret = os.environ.get("SLACK_SIGNING_SECRET", "")
    if not secret:
        raise SystemExit("SLACK_SIGNING_SECRET required")

    queue = EventQueue(path=__import__("pathlib").Path(args.queue))

    def handler(payload: dict) -> None:
        event = payload.get("event") or {}
        record = SourceEvent(
            event_id=str(payload.get("event_id") or event.get("ts") or utc_now_iso()),
            source="slack",
            event_type=str(event.get("type") or "unknown"),
            native_id=f"{event.get('channel')}:{event.get('ts')}" if event.get("channel") and event.get("ts") else None,
            payload=payload,
            received_at=utc_now_iso(),
        )
        queue.enqueue(record)

    gateway = SlackEventsGateway(signing_secret=secret, handler=handler)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            headers = {k: v for k, v in self.headers.items()}
            code, resp = gateway.handle_http(body, headers)
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode("utf-8"))

        def log_message(self, format, *args):  # noqa: A003
            return

    server = HTTPServer((args.host, args.port), Handler)
    print(f"Slack events gateway on http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
