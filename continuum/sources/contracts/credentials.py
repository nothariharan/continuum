"""Encrypted connector credential storage (founder implements)."""

from __future__ import annotations

from typing import Protocol


class ConnectorCredentialsStore(Protocol):
    """Persist OAuth tokens and secrets per tenant + connected source."""

    def save_encrypted(
        self,
        *,
        tenant_id: str,
        source_id: str,
        provider: str,
        plaintext: bytes,
    ) -> None: ...

    def load_decrypted(self, *, tenant_id: str, source_id: str) -> bytes: ...

    def delete(self, *, tenant_id: str, source_id: str) -> None: ...
