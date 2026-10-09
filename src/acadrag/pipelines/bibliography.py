"""Stage 2: document metadata and references via Grobid.

For each pending ``bibliography`` job:

1. Call ``processHeaderDocument``. Save the raw BibTeX to disk.
   Parse it; if a title is present, upsert ``document_metadata`` and
   set ``documents.has_metadata = True``; else set has_metadata = False
   and flag needs_review.
2. Call ``processFulltextDocument``. Save the TEI; parse references;
   replace rows in the ``references`` table. Set has_metadata stays
   as decided in step 1.

Error handling:
  * GrobidUnavailable  -> PENDING; on max attempts, GAVE_UP.
  * GrobidError        -> FAILED.
  * Header parse empty -> DONE, has_metadata = False, needs_review.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from acadrag.config import Config
from acadrag.domain.job import JobStatus
from acadrag.services.bibtex import parse_bibtex
from acadrag.services.grobid import (
    GrobidClient,
    GrobidError,
    GrobidUnavailable,
)
from acadrag.services.tei import parse_references
from acadrag.storage.repositories.document_metadata import (
    DocumentMetadataRepository,
)
from acadrag.storage.repositories.documents import DocumentRepository
from acadrag.storage.repositories.jobs import JobRepository
from acadrag.storage.repositories.references import ReferencesRepository

log = logging.getLogger(__name__)

STAGE = "bibliography"
DEFAULT_MAX_ATTEMPTS = 5


def _process_one(
    doc,
    grobid: GrobidClient,
    doc_repo: DocumentRepository,
    meta_repo: DocumentMetadataRepository,
    refs_repo: ReferencesRepository,
) -> tuple[JobStatus, str | None]:
    """Process a single bibliography job."""
    pdf_path: Path = doc.stored_path
    doc_dir = pdf_path.parent

    # --- Step 1: header (document's own metadata) ---
    try:
        bibtex_text = grobid.process_header(pdf_path)
    except GrobidUnavailable as exc:
        return JobStatus.PENDING, f"unavailable: {exc}"
    except GrobidError as exc:
        return JobStatus.FAILED, f"grobid error: {exc}"

    (doc_dir / "header.bib").write_text(bibtex_text, encoding="utf-8")
    meta = parse_bibtex(bibtex_text)

    if meta is not None:
        meta_repo.upsert(doc.id, meta)
        doc_repo.set_has_metadata(doc.id, True)
    else:
        doc_repo.set_has_metadata(doc.id, False)
        doc_repo.set_needs_review(doc.id, True)

    # --- Step 2: full-text (references cited by the document) ---
    try:
        tei = grobid.process_pdf(pdf_path)
    except GrobidUnavailable as exc:
        return JobStatus.PENDING, f"unavailable (fulltext): {exc}"
    except GrobidError as exc:
        return JobStatus.FAILED, f"grobid error (fulltext): {exc}"

    (doc_dir / "grobid.tei.xml").write_text(tei, encoding="utf-8")
    refs = parse_references(tei)
    refs_repo.replace_for_document(doc.id, refs)
    (doc_dir / "references.json").write_text(
        json.dumps(refs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return JobStatus.DONE, None


def run_pending(
    cfg: Config,
    grobid: GrobidClient,
    doc_repo: DocumentRepository,
    job_repo: JobRepository,
    meta_repo: DocumentMetadataRepository,
    refs_repo: ReferencesRepository,
    *,
    max_jobs: int = 10,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> dict:
    """Process up to ``max_jobs`` pending bibliography jobs.

    Returns:
        Summary dict: ``{done, gave_up, failed, retried}``.
    """
    summary = {"done": 0, "gave_up": 0, "failed": 0, "retried": 0}

    if not grobid.is_available():
        log.warning("Grobid not reachable; skipping run.")
        return summary

    for _ in range(max_jobs):
        job = job_repo.next_pending(STAGE)
        if job is None:
            break

        doc = doc_repo.get_by_id(job.doc_id)
        if doc is None:
            job_repo.mark(
                job.id, JobStatus.FAILED,
                error="document row missing", bump_attempts=True,
            )
            summary["failed"] += 1
            continue

        status, error = _process_one(
            doc, grobid, doc_repo, meta_repo, refs_repo
        )

        if status is JobStatus.PENDING:
            attempts = job.attempts + 1
            if attempts >= max_attempts:
                job_repo.mark(
                    job.id, JobStatus.GAVE_UP,
                    error=error, bump_attempts=True,
                )
                doc_repo.set_needs_review(doc.id, True)
                summary["gave_up"] += 1
            else:
                job_repo.mark(
                    job.id, JobStatus.PENDING,
                    error=error, bump_attempts=True,
                )
                summary["retried"] += 1
        elif status is JobStatus.FAILED:
            job_repo.mark(
                job.id, JobStatus.FAILED,
                error=error, bump_attempts=True,
            )
            summary["failed"] += 1
        else:
            job_repo.mark(
                job.id, JobStatus.DONE,
                error=error, bump_attempts=True,
            )
            summary["done"] += 1

    return summary
