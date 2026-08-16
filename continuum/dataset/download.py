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


def benchmark_cache_dir(cache_dir: Path) -> Path:
    return cache_dir / "enterprise-rag-bench-v1.0.0"


def asset_path(cache_dir: Path, asset_name: str) -> Path:
    return benchmark_cache_dir(cache_dir) / asset_name


def download_asset(cache_dir: Path, asset_name: str, verify: bool = True) -> Path:
    """Download a pinned manifest asset with optional SHA-256 verification."""
    asset = asset_by_name(asset_name)
    if asset is None:
        raise RuntimeError(f"{asset_name} not found in pinned manifest")

    destination = asset_path(cache_dir, asset_name)
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        _download(asset["url"], destination)

    if verify:
        actual = _sha256(destination)
        if actual != asset["sha256"]:
            destination.unlink(missing_ok=True)
            raise RuntimeError(
                f"checksum mismatch for {asset_name}: expected {asset['sha256']}, got {actual}"
            )
    return destination


def download_questions_jsonl(cache_dir: Path, verify: bool = True) -> Path:
    return download_asset(cache_dir, "questions.jsonl", verify=verify)


def download_extra_questions_jsonl(cache_dir: Path, verify: bool = True) -> Path:
    return download_asset(cache_dir, "extra_questions.jsonl", verify=verify)


def all_documents_path(cache_dir: Path) -> Path:
    return benchmark_cache_dir(cache_dir) / "all_documents.zip"


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