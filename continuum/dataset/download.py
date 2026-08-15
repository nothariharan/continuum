"""Reproducible EnterpriseRAG-Bench v1.0.0 download and checksum verification."""

from __future__ import annotations

import hashlib
import shutil
import urllib.request
import zipfile
from pathlib import Path

from .manifest import asset_by_name, load_manifest

CHUNK = 1024 * 256


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, destination: Path) -> None:
    tmp = destination.with_suffix(".part")
    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", "continuum-phase2a")]
    if tmp.exists():
        tmp.unlink()
    with opener.open(url) as response, open(tmp, "wb") as out:
        shutil.copyfileobj(response, out, length=CHUNK)
    tmp.rename(destination)


def all_documents_path(cache_dir: Path) -> Path:
    return cache_dir / "enterprise-rag-bench-v1.0.0" / "all_documents.zip"


def download_all_documents(cache_dir: Path, verify: bool = True) -> Path:
    manifest = load_manifest()
    asset = asset_by_name("all_documents.zip")
    if asset is None:
        raise RuntimeError("all_documents.zip not found in pinned manifest")

    zip_path = all_documents_path(cache_dir)
    if not zip_path.exists():
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        _download(asset["url"], zip_path)

    if verify:
        actual = _sha256(zip_path)
        if actual != asset["sha256"]:
            zip_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"checksum mismatch for all_documents.zip: expected {asset['sha256']}, got {actual}"
            )
    return zip_path


def open_corpus(cache_dir: Path) -> zipfile.ZipFile:
    return zipfile.ZipFile(download_all_documents(cache_dir))