"""BibliographyRepository: persistence for extracted references."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import delete, insert, select

from acadrag.storage.db import bibliography
from acadrag.storage.repositories.base import BaseRepository


class BibliographyRepository(BaseRepository):
    """Read/write access to the ``bibliography`` table."""

    def replace_for_document(
        self, source_doc_id: int,
        refs: list[dict[str, Any]]
    ) -> None:
        """Replace all stored references for ``source_doc_id``.

        Idempotent: any existing rows for this document are removed
        first, then the new ones are inserted in order.
        """
        with self.engine.begin() as conn:
            conn.execute(
                delete(bibliography).where(
                    bibliography.c.source_doc_id == source_doc_id
                )
            )
            if not refs:
                return
            rows = []
            for ordinal, ref in enumerate(refs):
                authors = ref.get("authors") or []
                rows.append(
                    {
                        "source_doc_id": source_doc_id,
                        "ordinal": ordinal,
                        "raw_ref": ref.get("raw") or "",
                        "title": ref.get("title"),
                        "authors_json": json.dumps(authors, ensure_ascii=False),
                        "year": ref.get("year"),
                        "venue": ref.get("venue"),
                        "doi": ref.get("doi"),
                        "arxiv_id": ref.get("arxiv_id"),
                        "resolved_sha256": None,
                    }
                )
            conn.execute(insert(bibliography), rows)

    def list_for_document(self, source_doc_id: int) -> list[dict]:
        """Return all references for a document, ordered by ordinal."""
        with self.engine.begin() as conn:
            rows = conn.execute(
                select(bibliography)
                .where(bibliography.c.source_doc_id == source_doc_id)
                .order_by(bibliography.c.ordinal)
            ).all()
        return [dict(r._mapping) for r in rows]

    def count_for_document(self, source_doc_id: int) -> int:
        """Return the number of references stored for a document."""
        return len(self.list_for_document(source_doc_id))
