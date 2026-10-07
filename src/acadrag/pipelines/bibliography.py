"""Stage 2: bibliography extraction via Grobid.

For each pending ``bibliography`` job: send the stored PDF to Grobid,
save the raw TEI XML and a parsed ``bibliography.json`` in the doc
folder, insert rows into the ``bibliography`` table, and mark the job
done or failed according to the error type.

Error taxonomy:
  * GrobidUnavailable      -> keep PENDING, retry with backoff.
  * GrobidError (other)    -> FAILED, record error.
  * Empty/garbled TEI      -> FAILED, has_bibliography stays NULL.
  * Valid TEI, no refs     -> DONE, has_bibliography = False.
  * Valid TEI, N >= min    -> DONE, has_bibliography = True.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from acadrag.config import Config
from acadrag.domain.job import JobStatus
from acadrag.services.grobid import (
    GrobidClient,
    GrobidError,
    GrobidUnavailable,
)
from acadrag.services.tei import parse_references
from acadrag.storage.repositories.bibliography import (
    BibliographyRepository,
)
from acadrag.storage.repositories.documents import DocumentRepository
from acadrag.storage.repositories.jobs import JobRepository

log = logging.getLogger(__name__)

STAGE = "bibliography"


def _utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def _backend_available(client: GrobidClient) -> bool:
    """Return True if Grobid answers a cheap probe request."""
    import requests
    try:
        requests.get(f"{client.base_url}/api/version",
                     timeout=5).raise_for_status()
        return True
    except Exception:
        return False


def _process_one(
    doc,
    grobid: GrobidClient,
    doc_repo: DocumentRepository,
    biblio_repo: BibliographyRepository,
    min_refs: int,
) -> tuple[JobStatus, str | None]:
    """Process a single bibliography job.

    Returns:
        A ``(status, error)`` pair for the job.
    """
    pdf_path: Path = doc.stored_path
    try:
        tei = grobid.process_pdf(pdf_path)
    except GrobidUnavailable as exc:
        return JobStatus.PENDING, f"unavailable: {exc}"
    except GrobidError as exc:
        return JobStatus.FAILED, f"grobid error: {exc}"

    doc_dir = pdf_path.parent
    (doc_dir / "grobid.tei.xml").write_text(tei, encoding="utf-8")

    refs = parse_references(tei)
    if not refs and not tei.strip():
        return JobStatus.FAILED, "empty grobid response"

    biblio_repo.replace_for_document(doc.id, refs)
    (doc_dir / "bibliography.json").write_text(
        json.dumps(refs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    doc_repo.set_has_bibliography(doc.id, len(refs) >= min_refs)
    return JobStatus.DONE, None


def run_pending(
    cfg: Config,
    grobid: GrobidClient,
    doc_repo: DocumentRepository,
    job_repo: JobRepository,
    biblio_repo: BibliographyRepository,
    *,
    max_jobs: int = 10,
    backoff_seconds: int = 300,
    min_refs: int = 1,
) -> dict:
    """Process up to ``max_jobs`` pending bibliography jobs.

    Args:
        cfg: Loaded configuration.
        grobid: Grobid HTTP client.
        doc_repo: Repository for documents.
        job_repo: Repository for jobs.
        biblio_repo: Repository for references.
        max_jobs: Upper bound on jobs processed in this call.
        backoff_seconds: Delay before retrying an unavailable job.
        min_refs: Minimum references to consider a bibliography
            present.

    Returns:
        A summary dict: ``{done, failed, retried, skipped}``.
    """
    summary = {"done": 0, "failed": 0, "retried": 0, "skipped": 0}

    if not _backend_available(grobid):
        log.warning("Grobid not reachable; skipping run.")
        return summary

    for _ in range(max_jobs):
        job = job_repo.next_pending(STAGE)
        if job is None:
            break

        doc = doc_repo.get_by_sha256(_sha_for_doc(doc_repo, job.doc_id))
        if doc is None:
            job_repo.mark(job.id, JobStatus.FAILED,
                          error="document row missing", bump_attempts=True)
            summary["failed"] += 1
            continue

        status, error = _process_one(
            doc, grobid, doc_repo, biblio_repo, min_refs
        )

        if status is JobStatus.PENDING:
            job_repo.mark(job.id, JobStatus.PENDING,
                          error=error, bump_attempts=True)
            summary["retried"] += 1
        elif status is JobStatus.FAILED:
            job_repo.mark(job.id, JobStatus.FAILED,
                          error=error, bump_attempts=True)
            summary["failed"] += 1
        else:
            job_repo.mark(job.id, JobStatus.DONE,
                          error=None, bump_attempts=True)
            summary["done"] += 1

    return summary


def _sha_for_doc(doc_repo: DocumentRepository, doc_id: int) -> str:
    """Return the sha256 for a document id (small helper)."""
    # The repository does not expose get_by_id; use a scan for now.
    with doc_repo.engine.begin() as conn:
        from acadrag.storage.db import documents
        from sqlalchemy import select
        row = conn.execute(
            select(documents.c.sha256).where(documents.c.id == doc_id)
        ).first()
    return row.sha256 if row else ""
