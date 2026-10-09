"""ReferencesRepository: works cited by an ingested document."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import delete, insert, select

from acadrag.storage.db import references
from acadrag.storage.repositories.base import BaseRepository


class ReferencesRepository(BaseRepository):
    """Read/write access to the ``references`` table."""

    # TODO(stage2.1): add a deterministic `quality` column
    # (ok | partial | garbled) computed at insertion time, based on
    # presence of title / year / authors. Grobid's reference parsing
    # leaves ~10% of entries structurally valid but semantically
    # wrong; a later LLM repair stage will target only the flagged
    # rows. See discussion around the first 105-ref batch.
    def replace_for_document(
        self, source_doc_id: int, refs: list[dict[str, Any]]
    ) -> None:
        """Replace all stored references for ``source_doc_id``."""
        with self.engine.begin() as conn:
            conn.execute(
                delete(references).where(
                    references.c.source_doc_id == source_doc_id
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
                        "authors_json": json.dumps(
                            authors, ensure_ascii=False
                        ),
                        "year": ref.get("year"),
                        "venue": ref.get("venue"),
                        "doi": ref.get("doi"),
                        "arxiv_id": ref.get("arxiv_id"),
                        "resolved_sha256": None,
                    }
                )
            conn.execute(insert(references), rows)

    def list_for_document(self, source_doc_id: int) -> list[dict]:
        """Return all references for a document, ordered by ordinal."""
        with self.engine.begin() as conn:
            rows = conn.execute(
                select(references)
                .where(references.c.source_doc_id == source_doc_id)
                .order_by(references.c.ordinal)
            ).all()
        return [dict(r._mapping) for r in rows]

    def count_for_document(self, source_doc_id: int) -> int:
        """Return the number of references stored for a document."""
        return len(self.list_for_document(source_doc_id))
