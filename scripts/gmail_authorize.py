#!/usr/bin/env python3
"""One-time Gmail OAuth consent flow.

Run this ONCE, locally, in an environment with a browser. It opens Google's
consent screen, then writes a reusable token file that the live Gmail connector
refreshes automatically on every sync.

Prerequisites:
    pip install '.[google]'
    export GMAIL_CREDENTIALS_PATH=/path/to/oauth-client-secret.json
    # optional: export GMAIL_TOKEN_PATH=/path/to/gmail_token.json

Usage:
    python scripts/gmail_authorize.py

See docs/gmail-live-setup.md for the Google Cloud project setup steps.
"""

from __future__ import annotations

from continuum.sources.gmail.oauth import GmailCredentials, run_oauth_flow


def main() -> int:
    creds = GmailCredentials.from_env()
    print(f"Using OAuth client secret: {creds.credentials_path}")
    token_path = run_oauth_flow(creds)
    print(f"✓ Consent granted. Token saved to: {token_path}")
    print("You can now run: python scripts/ingest_gmail.py --mode live --query 'label:continuum-demo'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
