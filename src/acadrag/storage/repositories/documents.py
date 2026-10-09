"""DocumentRepository: persistence for :class:`Document`."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, insert, select, update

from acadrag.domain.document import Document, DocumentStatus
from acadrag.storage.db import documents
from acadrag.storage.repositories.base import BaseRepository


def _row_to_doc(row) -> Document:
    """Convert a ``documents`` row into a :class:`Document`."""
    return Document(
        id=row.id,
        sha256=row.sha256,
        original_name=row.original_name,
        original_path=Path(row.original_path),
        stored_path=Path(row.stored_path),
        size_bytes=row.size_bytes,
        status=DocumentStatus(row.status),
        doc_type=row.doc_type,
        intent=row.intent,
        has_metadata=row.has_metadata,
        needs_review=bool(row.needs_review),
        ingested_at=row.ingested_at,
    )


class DocumentRepository(BaseRepository):
    """Read/write access to the ``documents`` table."""

    def add(self, doc: Document) -> int:
        """Insert ``doc`` and return its assigned primary key."""
        with self.engine.begin() as conn:
            result = conn.execute(
                insert(documents).values(
                    sha256=doc.sha256,
                    original_name=doc.original_name,
                    original_path=str(doc.original_path),
                    stored_path=str(doc.stored_path),
                    size_bytes=doc.size_bytes,
                    status=doc.status.value,
                    doc_type=doc.doc_type,
                    intent=doc.intent,
                    has_metadata=doc.has_metadata,
                    needs_review=doc.needs_review,
                    ingested_at=doc.ingested_at,
                )
            )
            return int(result.inserted_primary_key[0])

    def get_by_id(self, doc_id: int) -> Document | None:
        """Return the document with the given primary key, or None."""
        with self.engine.begin() as conn:
            row = conn.execute(
                select(documents).where(documents.c.id == doc_id)
            ).first()
        return _row_to_doc(row) if row else None

    def get_by_sha256(self, sha256: str) -> Document | None:
        """Return the document with the given hash, or ``None``."""
        with self.engine.begin() as conn:
            row = conn.execute(
                select(documents).where(documents.c.sha256 == sha256)
            ).first()
        return _row_to_doc(row) if row else None

    def exists(self, sha256: str) -> bool:
        """Return True if a document with this hash is known."""
        return self.get_by_sha256(sha256) is not None

    def list_by_status(
        self, status: DocumentStatus
    ) -> list[Document]:
        """Return all documents currently in ``status``."""
        with self.engine.begin() as conn:
            rows = conn.execute(
                select(documents).where(
                    documents.c.status == status.value
                )
            ).all()
        return [_row_to_doc(r) for r in rows]

    def update_status(
        self, doc_id: int, status: DocumentStatus
    ) -> None:
        """Set the status of document ``doc_id``."""
        with self.engine.begin() as conn:
            conn.execute(
                update(documents)
                .where(documents.c.id == doc_id)
                .values(status=status.value)
            )

    def set_has_metadata(
        self, doc_id: int, value: bool | None
    ) -> None:
        """Record whether the document's own metadata was found."""
        with self.engine.begin() as conn:
            conn.execute(
                update(documents)
                .where(documents.c.id == doc_id)
                .values(has_metadata=value)
            )

    def set_needs_review(self, doc_id: int, value: bool) -> None:
        """Set the needs_review flag on a document."""
        with self.engine.begin() as conn:
            conn.execute(
                update(documents)
                .where(documents.c.id == doc_id)
                .values(needs_review=value)
            )

    def count(self) -> int:
        """Return the total number of documents."""
        with self.engine.begin() as conn:
            result = conn.execute(
                select(func.count()).select_from(documents)
            ).scalar_one()
        return int(result)
