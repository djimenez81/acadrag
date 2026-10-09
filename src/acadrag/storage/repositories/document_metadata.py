"""DocumentMetadataRepository: a document's own bibliographic identity."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import delete, insert, select

from acadrag.storage.db import document_metadata
from acadrag.storage.repositories.base import BaseRepository


class DocumentMetadataRepository(BaseRepository):
    """Read/write access to the ``document_metadata`` table."""

    def upsert(
        self, document_id: int, fields: dict[str, Any]
    ) -> None:
        """Insert or replace the metadata row for ``document_id``.

        Args:
            document_id: The document this metadata describes.
            fields: Keys among title, authors, year, venue, doi,
                arxiv_id, abstract, raw_bibtex.
        """
        authors = fields.get("authors") or []
        row = {
            "document_id": document_id,
            "title": fields.get("title"),
            "authors_json": json.dumps(authors, ensure_ascii=False),
            "year": fields.get("year"),
            "venue": fields.get("venue"),
            "doi": fields.get("doi"),
            "arxiv_id": fields.get("arxiv_id"),
            "abstract": fields.get("abstract"),
            "raw_bibtex": fields.get("raw_bibtex"),
        }
        with self.engine.begin() as conn:
            conn.execute(
                delete(document_metadata).where(
                    document_metadata.c.document_id == document_id
                )
            )
            conn.execute(insert(document_metadata).values(**row))

    def get(self, document_id: int) -> dict[str, Any] | None:
        """Return the metadata row for a document, or ``None``."""
        with self.engine.begin() as conn:
            row = conn.execute(
                select(document_metadata).where(
                    document_metadata.c.document_id == document_id
                )
            ).first()
        if row is None:
            return None
        data = dict(row._mapping)
        try:
            data["authors"] = json.loads(data.pop("authors_json") or "[]")
        except json.JSONDecodeError:
            data["authors"] = []
        return data
