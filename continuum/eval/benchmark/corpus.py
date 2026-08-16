"""Corpus loading for benchmark modes."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from continuum.dataset.artifact import Artifact
from continuum.dataset.download import download_all_documents, open_corpus

from .schema import DEFAULT_RAW, DEFAULT_SAMPLE_CORPUS


@dataclass
class CorpusRecord:
    artifact_id: str
    source: str
    title: str
    content: str

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.content}"

    def to_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "source": self.source,
            "title": self.title,
        }


@dataclass
class BenchmarkCorpus:
    mode: str
    records: list[CorpusRecord]

    @property
    def texts(self) -> list[str]:
        return [record.text for record in self.records]

    @property
    def ids(self) -> list[str]:
        return [record.artifact_id for record in self.records]

    @property
    def id_set(self) -> set[str]:
        return set(self.ids)

    def record_by_id(self) -> dict[str, CorpusRecord]:
        return {record.artifact_id: record for record in self.records}


def load_sample_corpus(path: Path | None = None) -> BenchmarkCorpus:
    corpus_path = path or DEFAULT_SAMPLE_CORPUS
    records: list[CorpusRecord] = []
    with corpus_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            records.append(
                CorpusRecord(
                    artifact_id=str(row["id"]),
                    source=str(row.get("source") or ""),
                    title=str(row.get("title") or ""),
                    content=str(row.get("content") or ""),
                )
            )
    return BenchmarkCorpus(mode="sample-v1", records=records)


def count_full_corpus_records(raw_dir: Path | None = None) -> int:
    cache = raw_dir or DEFAULT_RAW
    download_all_documents(cache)
    with open_corpus(cache) as archive:
        return sum(1 for name in archive.namelist() if name.endswith(".txt"))


def load_full_corpus(raw_dir: Path | None = None, *, limit: int = 0) -> BenchmarkCorpus:
    """Load normalized artifacts from the pinned all_documents.zip."""
    cache = raw_dir or DEFAULT_RAW
    download_all_documents(cache)
    records: list[CorpusRecord] = []
    with open_corpus(cache) as archive:
        names = sorted(name for name in archive.namelist() if name.endswith(".txt"))
        if limit:
            names = names[:limit]
        for name in names:
            raw = archive.read(name).decode("utf-8", errors="replace")
            source = name.split("/", 1)[0]
            artifact = Artifact.from_raw(source, name, raw)
            records.append(
                CorpusRecord(
                    artifact_id=artifact.id,
                    source=artifact.source,
                    title=artifact.title,
                    content=artifact.content,
                )
            )
    return BenchmarkCorpus(mode="full-v1", records=records)


def load_corpus(mode: str, *, raw_dir: Path | None = None, corpus_limit: int = 0) -> BenchmarkCorpus:
    if mode == "sample-v1":
        return load_sample_corpus()
    if mode == "full-v1":
        return load_full_corpus(raw_dir, limit=corpus_limit)
    raise ValueError(f"unknown corpus mode: {mode}")
