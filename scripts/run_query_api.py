#!/usr/bin/env python3
"""Run Continuum Query API (FastAPI)."""

from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        raise SystemExit("Install delivery deps: pip install fastapi uvicorn")

    from continuum.delivery.api import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
