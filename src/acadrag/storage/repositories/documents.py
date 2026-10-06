"""DocumentRepository — the only place that writes SQL for `documents`."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from sqlalchemy import insert, select, update

from acadrag.domain.document import Document, DocumentStatus
from acadrag.storage.db import documents
from acadrag.storage.repositories.base import BaseRepository


def _row_to_doc(row) -> Document:
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
        needs_review=bool(row.needs_review),
        ingested_at=row.ingested_at,
    )


class DocumentRepository(BaseRepository):
    def add(self, doc: Document) -> int:
        with self.engine.begin() as conn:
            result = conn.execute(insert(documents).values(
                sha256=doc.sha256,
                original_name=doc.original_name,
                original_path=str(doc.original_path),
                stored_path=str(doc.stored_path),
                size_bytes=doc.size_bytes,
                status=doc.status.value,
                doc_type=doc.doc_type,
                intent=doc.intent,
                needs_review=doc.needs_review,
                ingested_at=doc.ingested_at,
            ))
            return int(result.inserted_primary_key[0])

    def get_by_sha256(self, sha256: str) -> Document | None:
        with self.engine.begin() as conn:
            row = conn.execute(
                select(documents).where(documents.c.sha256 == sha256)
            ).first()
        return _row_to_doc(row) if row else None

    def exists(self, sha256: str) -> bool:
        return self.get_by_sha256(sha256) is not None

    def list_by_status(self, status: DocumentStatus) -> list[Document]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                select(documents).where(documents.c.status == status.value)
            ).all()
        return [_row_to_doc(r) for r in rows]

    def update_status(self, doc_id: int, status: DocumentStatus) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                update(documents).where(documents.c.id == doc_id).values(status=status.value)
            )

    def count(self) -> int:
        with self.engine.begin() as conn:
            return int(conn.execute(select(documents.c.id)).rowcount or 0)
