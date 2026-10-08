"""Stage 1: ingest.

Scan the inbox, hash each file, decide seen/unseen, and route it to
``processed/`` (with a DB record) or ``rejected/``. Idempotent: re-
running on the same inbox is a no-op.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from acadrag.config import Config
from acadrag.domain.document import Document, DocumentStatus
from acadrag.storage.filesystem import FileStore
from acadrag.storage.repositories.documents import DocumentRepository
from acadrag.storage.repositories.jobs import JobRepository

log = logging.getLogger(__name__)


def sha256_of(path: Path, chunk_size: int = 1 << 20) -> str:
    """Return the hex SHA-256 digest of the file at ``path``.

    Args:
        path: File to hash.
        chunk_size: Read size in bytes per iteration.

    Returns:
        Lowercase hex digest.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk_size), b""):
            digest.update(block)
    return digest.hexdigest()


def ingest_once(
    cfg: Config,
    doc_repo: DocumentRepository,
    store: FileStore,
    job_repo: JobRepository | None = None,
) -> dict:
    """Process every file currently in the inbox exactly once.

    Args:
        cfg: Loaded configuration.
        doc_repo: Repository for document records.
        store: Filesystem helper for canonical storage.
        job_repo: If given, enqueue a ``bibliography`` job for each
            newly ingested document.

    Returns:
        A summary dict with keys ``processed``, ``duplicates``,
        ``rejected``, and ``errors``.
    """
    summary = {
        "processed": 0,
        "duplicates": 0,
        "rejected": 0,
        "errors": 0,
    }
    inbox = cfg.paths.inbox

    for src in sorted(p for p in inbox.iterdir() if p.is_file()):
        try:
            digest = sha256_of(src)
        except OSError as exc:
            log.warning("Could not hash %s: %s", src, exc)
            store.reject(src, "unreadable")
            summary["errors"] += 1
            continue

        if doc_repo.get_by_sha256(digest) is not None:
            store.reject(src, "duplicate")
            summary["duplicates"] += 1
            continue

        stored = store.store(src, digest)
        doc = Document(
            sha256=digest,
            original_name=src.name,
            original_path=src,
            stored_path=stored,
            size_bytes=stored.stat().st_size,
            status=DocumentStatus.INGESTED,
        )
        doc.id = doc_repo.add(doc)
        if job_repo is not None:
            job_repo.enqueue(doc.id, "bibliography")
            job_repo.enqueue(doc.id, "convert")
        store.remove_from_inbox(src)
        summary["processed"] += 1

    return summary
