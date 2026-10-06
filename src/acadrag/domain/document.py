"""Domain object: a document tracked by acadrag."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


class DocumentStatus(str, Enum):
    INGESTED = "ingested"        # hashed, moved into processed/, DB row exists
    CONVERTED = "converted"      # markdown available
    BIBLIO_DONE = "biblio_done"
    CLASSIFIED = "classified"
    CHUNKED = "chunked"
    EMBEDDED = "embedded"
    SUMMARIZED = "summarized"
    ENTITIES_DONE = "entities_done"
    FAILED = "failed"


@dataclass
class Document:
    sha256: str
    original_name: str
    original_path: Path           # where it was picked up from
    stored_path: Path             # canonical location under processed/
    size_bytes: int
    status: DocumentStatus = DocumentStatus.INGESTED
    doc_type: str | None = None   # taxonomy label (paper, book, ...)
    intent: str | None = None     # e.g., research / teaching / competition
    needs_review: bool = False
    id: int | None = None
    ingested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
