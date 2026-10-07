"""JobRepository: persistence for the retry queue."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import insert, select, update

from acadrag.domain.job import Job, JobStatus
from acadrag.storage.db import jobs
from acadrag.storage.repositories.base import BaseRepository


def _utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def _row_to_job(row) -> Job:
    """Convert a ``jobs`` row into a :class:`Job`."""
    return Job(
        id=row.id,
        doc_id=row.doc_id,
        stage=row.stage,
        status=JobStatus(row.status),
        attempts=row.attempts,
        last_error=row.last_error,
        next_retry_at=row.next_retry_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class JobRepository(BaseRepository):
    """Read/write access to the ``jobs`` table."""

    def enqueue(self, doc_id: int, stage: str) -> int:
        """Insert a new pending job and return its primary key."""
        now = _utcnow()
        with self.engine.begin() as conn:
            result = conn.execute(
                insert(jobs).values(
                    doc_id=doc_id,
                    stage=stage,
                    status=JobStatus.PENDING.value,
                    attempts=0,
                    created_at=now,
                    updated_at=now,
                )
            )
            return int(result.inserted_primary_key[0])

    def next_pending(self, stage: str | None = None) -> Job | None:
        """Return the oldest pending job, optionally of a given stage."""
        stmt = select(jobs).where(
            jobs.c.status == JobStatus.PENDING.value
        )
        if stage:
            stmt = stmt.where(jobs.c.stage == stage)
        with self.engine.begin() as conn:
            row = conn.execute(stmt.order_by(jobs.c.id).limit(1)).first()
        return _row_to_job(row) if row else None

    def mark(
        self,
        job_id: int,
        status: JobStatus,
        *,
        error: str | None = None,
        bump_attempts: bool = False,
    ) -> None:
        """Update the status of ``job_id``.

        Args:
            job_id: Primary key of the job.
            status: New status.
            error: Optional error message to record.
            bump_attempts: If True, increment ``attempts`` by one.
        """
        now = _utcnow()
        values: dict = {"status": status.value, "updated_at": now}
        if error is not None:
            values["last_error"] = error
        with self.engine.begin() as conn:
            if bump_attempts:
                conn.execute(
                    update(jobs)
                    .where(jobs.c.id == job_id)
                    .values(attempts=jobs.c.attempts + 1, **values)
                )
            else:
                conn.execute(
                    update(jobs)
                    .where(jobs.c.id == job_id)
                    .values(**values)
                )
