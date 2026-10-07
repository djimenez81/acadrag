"""Domain object: a unit of work tracked by the orchestration layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class JobStatus(str, Enum):
    """Statuses of a job tracked by acadrag."""
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Job:
    """A job tracked by acadrag."""
    doc_id: int
    stage: str                    # e.g. "ingest", "bibliography", "classify"
    status: JobStatus = JobStatus.PENDING
    attempts: int = 0
    last_error: str | None = None
    next_retry_at: datetime | None = None
    id: int | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
