"""Domain object: a document tracked by acadrag."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


def _utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class DocumentStatus(str, Enum):
    """Lifecycle states a document passes through."""

    INGESTED = "ingested"
    CONVERTED = "converted"
    BIBLIO_DONE = "biblio_done"
    CLASSIFIED = "classified"
    CHUNKED = "chunked"
    EMBEDDED = "embedded"
    SUMMARIZED = "summarized"
    ENTITIES_DONE = "entities_done"
    FAILED = "failed"


@dataclass
class Document:
    """A single file tracked by acadrag.

    Attributes:
        sha256: Content hash; the document's identity.
        original_name: Filename as provided by the user.
        original_path: Path the file was picked up from.
        stored_path: Canonical location under ``paths.processed``.
        size_bytes: File size in bytes.
        status: Current lifecycle status.
        doc_type: Taxonomy label (e.g. ``"paper"``), if classified.
        intent: Intent label (e.g. ``"research"``), if classified.
        has_bibliography: True/False/None (unknown).
        needs_review: True if the user must resolve ambiguity.
        id: Primary key assigned by the database, if persisted.
        ingested_at: UTC timestamp of ingestion.
    """

    sha256: str
    original_name: str
    original_path: Path
    stored_path: Path
    size_bytes: int
    status: DocumentStatus = DocumentStatus.INGESTED
    doc_type: str | None = None
    intent: str | None = None
    has_bibliography: bool | None = None
    needs_review: bool = False
    id: int | None = None
    ingested_at: datetime = field(default_factory=_utcnow)
