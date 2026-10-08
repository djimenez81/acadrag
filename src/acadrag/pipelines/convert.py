"""Stage 3: PDF→Markdown conversion.

For each pending ``convert`` job: run the backend chain, write
``document.md`` and ``document.meta.json`` into the doc folder, run a
sanity check, and mark the job done or failed.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from acadrag.config import Config
from acadrag.domain.document import DocumentStatus
from acadrag.domain.job import JobStatus
from acadrag.services.converter import get_backend
from acadrag.storage.repositories.documents import DocumentRepository
from acadrag.storage.repositories.jobs import JobRepository

log = logging.getLogger(__name__)

STAGE = "convert"


def _run_backend_chain(
    cfg: Config, pdf_path: Path
) -> tuple[str | None, dict, str | None]:
    """Try primary backend, then fallback.

    Returns:
        ``(markdown, metadata, error)``. On total failure, markdown is
        ``None`` and error is set.
    """
    convert_cfg = cfg.stages.get("convert", {})
    primary = convert_cfg.get("backend", "marker")
    fallback = convert_cfg.get("fallback")

    for name in [primary] + ([fallback] if fallback else []):
        try:
            backend = get_backend(cfg, name)
            result = backend.convert(pdf_path)
            if not result.markdown or not result.markdown.strip():
                log.warning("%s produced empty output", name)
                continue
            return result.markdown, result.metadata, None
        except Exception as exc:
            log.warning("%s failed: %s", name, exc)
            last_error = f"{name}: {exc}"

    return None, {}, last_error


def _process_one(
    doc,
    cfg: Config,
    doc_repo: DocumentRepository,
) -> tuple[JobStatus, str | None]:
    """Convert one document and write its artifacts.

    Returns:
        ``(status, error)``.
    """
    pdf_path: Path = doc.stored_path
    convert_cfg = cfg.stages.get("convert", {})

    markdown, metadata, error = _run_backend_chain(cfg, pdf_path)
    if markdown is None:
        return JobStatus.FAILED, error

    doc_dir = pdf_path.parent
    (doc_dir / "document.md").write_text(markdown, encoding="utf-8")

    page_count = metadata.get("page_count") or metadata.get("pages")
    min_ratio = convert_cfg.get("sanity", {}).get("min_word_ratio", 0.3)
    if page_count and page_count > 0:
        expected = page_count * 200
        ratio = metadata["word_count"] / expected
        metadata["word_ratio"] = round(ratio, 3)
        if ratio < min_ratio:
            metadata["warning"] = "low word ratio"
            doc_repo.set_needs_review(doc.id, True)

    (doc_dir / "document.meta.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return JobStatus.DONE, None


def run_pending(
    cfg: Config,
    doc_repo: DocumentRepository,
    job_repo: JobRepository,
    *,
    max_jobs: int = 5,
) -> dict:
    """Process up to ``max_jobs`` pending convert jobs.

    Returns:
        Summary dict: ``{done, failed, retried}``.
    """
    summary = {"done": 0, "failed": 0, "retried": 0}

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

        status, error = _process_one(doc, cfg, doc_repo)

        if status is JobStatus.FAILED:
            job_repo.mark(
                job.id, JobStatus.FAILED,
                error=error, bump_attempts=True,
            )
            summary["failed"] += 1
        else:
            job_repo.mark(
                job.id, JobStatus.DONE,
                error=None, bump_attempts=True,
            )
            doc_repo.update_status(doc.id, DocumentStatus.CONVERTED)
            summary["done"] += 1

    return summary
