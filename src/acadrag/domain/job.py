"""Domain object: a unit of work tracked by the orchestration layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class JobStatus(str, Enum):
    """States a job can be in.

    Attributes:
        PENDING: Eligible to be picked up by the next run.
        RUNNING: Currently being processed.
        DONE: Completed successfully.
        GAVE_UP: Terminal; attempts exhausted. See ``last_error`` for
            the reason and ``documents.needs_review`` on the parent.
        FAILED: Terminal; the code itself could not proceed (bug,
            invalid state). Not for external-service outages.
    """

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    GAVE_UP = "gave_up"
    FAILED = "failed"


@dataclass
class Job:
    """A retryable unit of work associated with a document.

    Attributes:
        doc_id: Foreign key to ``documents.id``.
        stage: Stage name (e.g. ``"bibliography"``).
        status: Current job status.
        attempts: Number of times this job has been attempted.
        last_error: Last error message, if any.
        next_retry_at: When the job becomes eligible again, if any.
        id: Primary key assigned by the database, if persisted.
        created_at: UTC timestamp of creation.
        updated_at: UTC timestamp of last update.
    """

    doc_id: int
    stage: str
    status: JobStatus = JobStatus.PENDING
    attempts: int = 0
    last_error: str | None = None
    next_retry_at: datetime | None = None
    id: int | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
