"""Environment-driven HydraDB configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    path = Path(os.getenv("CONTINUUM_ENV_FILE", ".env"))
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class HydraDBConfig:
    host: str = "127.0.0.1"
    bolt_port: int = 7687
    http_port: int = 8443
    admin_port: int = 9090
    user: str = "neo4j"
    password: str = "local-development-token-32-characters-long"
    database: str = "default"
    namespace: str = "default"
    cell_id: str = "cell-0"
    protocol: str = "bolt"
    image: str = "ghcr.io/hydra-db/hydradb@sha256:db78309a233be54662db29744047e985a39b51c45a270d1a1f47c31a62cdb709"
    container_name: str = "continuum-hydradb"
    state_dir: Path = Path("hydradb-data")

    @classmethod
    def from_env(cls) -> "HydraDBConfig":
        _load_dotenv()
        return cls(
            host=os.getenv("HYDRADB_HOST", cls.host),
            bolt_port=int(os.getenv("HYDRADB_BOLT_PORT", cls.bolt_port)),
            http_port=int(os.getenv("HYDRADB_HTTP_PORT", cls.http_port)),
            admin_port=int(os.getenv("HYDRADB_ADMIN_PORT", cls.admin_port)),
            user=os.getenv("HYDRADB_USER", cls.user),
            password=os.getenv("HYDRADB_PASSWORD", cls.password),
            database=os.getenv("HYDRADB_DATABASE", cls.database),
            namespace=os.getenv("HYDRADB_NAMESPACE", cls.namespace),
            cell_id=os.getenv("HYDRADB_CELL_ID", cls.cell_id),
            protocol=os.getenv("HYDRADB_PROTOCOL", cls.protocol),
            image=os.getenv("HYDRADB_IMAGE", cls.image),
            container_name=os.getenv("HYDRADB_CONTAINER_NAME", cls.container_name),
            state_dir=Path(os.getenv("HYDRADB_STATE_DIR", str(cls.state_dir))),
        )

    @property
    def bolt_uri(self) -> str:
        return f"{self.protocol}://{self.host}:{self.bolt_port}"

    @property
    def admin_ready_url(self) -> str:
        return f"http://{self.host}:{self.admin_port}/readyz"
