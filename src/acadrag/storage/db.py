"""SQLAlchemy Core engine and schema definition.

The schema is intentionally minimal and grows as stages are added.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
)
from sqlalchemy.engine import Engine

metadata = MetaData()

documents = Table(
    "documents",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("sha256", String(64), unique=True, nullable=False),
    Column("original_name", String, nullable=False),
    Column("original_path", String, nullable=False),
    Column("stored_path", String, nullable=False),
    Column("size_bytes", Integer, nullable=False),
    Column("status", String, nullable=False, default="ingested"),
    Column("doc_type", String, nullable=True),
    Column("intent", String, nullable=True),
    Column("has_bibliography", Boolean, nullable=True),
    Column("needs_review", Boolean, nullable=False, default=False),
    Column("ingested_at", DateTime, nullable=False),
)

jobs = Table(
    "jobs",
    metadata,
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

bibliography = Table(
    "bibliography",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "source_doc_id",
        Integer,
        ForeignKey("documents.id"),
        nullable=False,
    ),
    Column("ordinal", Integer, nullable=False),
    Column("raw_ref", Text, nullable=False),
    Column("title", Text, nullable=True),
    Column("authors_json", Text, nullable=True),
    Column("year", Integer, nullable=True),
    Column("venue", Text, nullable=True),
    Column("doi", String, nullable=True),
    Column("arxiv_id", String, nullable=True),
    Column("resolved_sha256", String(64), nullable=True),
)


def make_engine(url: str) -> Engine:
    """Create a SQLAlchemy engine and ensure the schema exists.

    Args:
        url: SQLAlchemy database URL.

    Returns:
        A configured :class:`Engine` with all tables created.
    """
    engine = create_engine(url, future=True)
    metadata.create_all(engine)
    return engine
