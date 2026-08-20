# Gmail Live Ingestion — Setup

Continuum ingests Gmail through the same `SourceConnector` contract as Slack.
The connector is **fixtures-first**: everything runs deterministically from
`data/fixtures/sources/gmail/` with no credentials. This doc covers wiring the
**live** path against a real (ideally dedicated demo) mailbox.

> Scope on purpose stays narrow — a bounded query and message count — so the
> first live integration is deterministic and cheap. Start with a label like
> `continuum-demo` on a test account, not your whole inbox.

## 1. Install the optional Google dependencies

```bash
pip install '.[google]'   # google-api-python-client, google-auth-oauthlib
```

The rest of Continuum runs without these; they are imported lazily and only
needed for the live path.

## 2. Create a Google Cloud OAuth client (human, one-time)

1. Go to <https://console.cloud.google.com/> and create (or pick) a project.
2. **APIs & Services → Library →** enable the **Gmail API**.
3. **APIs & Services → OAuth consent screen:** choose *External* (or *Internal*
   for a Workspace), add yourself as a **Test user**. Scope needed:
   `https://www.googleapis.com/auth/gmail.readonly` (read-only — Continuum never
   writes to your mailbox).
4. **APIs & Services → Credentials → Create credentials → OAuth client ID →
   Application type: Desktop app.** Download the JSON. This is your
   **client secret** file.

## 3. Point Continuum at the credentials

```bash
export GMAIL_CREDENTIALS_PATH=/absolute/path/to/oauth-client-secret.json
# optional; defaults to gmail_token.json next to the secret:
export GMAIL_TOKEN_PATH=/absolute/path/to/gmail_token.json
```

**Never commit** the client secret, the token, or any access/refresh tokens.
They are secrets and are `.gitignore`d.

## 4. Grant consent once

```bash
python scripts/gmail_authorize.py
```

A browser opens, you approve read-only access, and a token file is written.
The connector refreshes the access token automatically afterward — you do not
repeat this step unless you revoke access.

## 5. Ingest

```bash
# initial bounded sync from a label
python scripts/ingest_gmail.py --mode live --query 'label:continuum-demo' --limit 100

# later, incremental (uses the Gmail History API via a stored historyId cursor)
python scripts/ingest_gmail.py --mode live --query 'label:continuum-demo' --incremental
```

## How incremental sync works

- Initial sync stores the mailbox **`historyId`** as the cursor watermark.
- Incremental sync calls the Gmail **History API** (`users.history.list`,
  `messageAdded`) from that watermark and advances it.
- If the stored `historyId` is too old for Gmail to serve (a `404`), the
  connector falls back to a **bounded resync** so ingestion never silently
  stalls — it does not reprocess the whole mailbox.

## Failure modes (surfaced, never hidden)

| Condition | Signal |
|-----------|--------|
| Missing/invalid credentials | `GmailLiveError(code="GMAIL_AUTH_FAILURE")` / `FileNotFoundError` |
| Missing google deps | `GmailAuthError` with `pip install '.[google]'` hint |
| API 401/403 | `GMAIL_AUTH_FAILURE` |
| API 429 / 5xx | `GmailLiveError(retryable=True)` |
| Other API error | `GMAIL_INGESTION_FAILURE` |

## Testing without any of this

The live client accepts an injected `service=` object (a fake mirroring the
`googleapiclient` resource chain). See `tests/sources/test_gmail_live.py` —
the entire live code path is unit-tested with no network, deps, or credentials.
