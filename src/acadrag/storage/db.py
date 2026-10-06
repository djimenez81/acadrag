"""SQLAlchemy Core engine + schema creation.

Schema is intentionally minimal for now; tables are added as stages land.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, MetaData, String, Table, Text,
    create_engine,
)
from sqlalchemy.engine import Engine

metadata = MetaData()

documents = Table(
    "documents", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("sha256", String(64), unique=True, nullable=False),
    Column("original_name", String, nullable=False),
    Column("original_path", String, nullable=False),
    Column("stored_path", String, nullable=False),
    Column("size_bytes", Integer, nullable=False),
    Column("status", String, nullable=False, default="ingested"),
    Column("doc_type", String, nullable=True),
    Column("intent", String, nullable=True),
    Column("needs_review", Boolean, nullable=False, default=False),
    Column("ingested_at", DateTime, nullable=False),
)

jobs = Table(
    "jobs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("doc_id", Integer, ForeignKey("documents.id"), nullable=False),
    Column("stage", String, nullable=False),
    Column("status", String, nullable=False, default="pending"),
    Column("attempts", Integer, nullable=False, default=0),
    Column("last_error", Text, nullable=True),
    Column("next_retry_at", DateTime, nullable=True),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)


def make_engine(url: str) -> Engine:
    """Create an engine and ensure the schema exists."""
    engine = create_engine(url, future=True)
    metadata.create_all(engine)
    return engine
