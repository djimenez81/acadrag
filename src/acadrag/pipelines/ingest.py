"""Stage 1: ingest.

Scan the inbox, hash each file, decide seen/unseen, and route it to
processed/ (with DB record) or rejected/. The ingest pipeline is
idempotent: re-running on the same file is a no-op.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from acadrag.config import Config
from acadrag.domain.document import Document, DocumentStatus
from acadrag.storage.filesystem import FileStore
from acadrag.storage.repositories.documents import DocumentRepository

log = logging.getLogger(__name__)


def sha256_of(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(chunk_size), b""):
            h.update(block)
    return h.hexdigest()


def ingest_once(cfg: Config, doc_repo: DocumentRepository, store: FileStore) -> dict:
    """Process every file currently in the inbox exactly once.

    Returns a small summary dict: {processed, duplicates, rejected, errors}.
    """
    summary = {"processed": 0, "duplicates": 0, "rejected": 0, "errors": 0}
    inbox = cfg.paths.inbox

    for src in sorted(p for p in inbox.iterdir() if p.is_file()):
        try:
            digest = sha256_of(src)
        except OSError as e:
            log.warning("Could not hash %s: %s", src, e)
            store.reject(src, "unreadable")
            summary["errors"] += 1
            continue

        existing = doc_repo.get_by_sha256(digest)
        if existing is not None:
            # Already known: discard the new copy.
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
        store.remove_from_inbox(src)
        summary["processed"] += 1

    return summary
