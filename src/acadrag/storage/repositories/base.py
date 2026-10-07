"""Shared helpers for repository classes."""

from __future__ import annotations

from sqlalchemy.engine import Engine


class BaseRepository:
    """Base class holding a SQLAlchemy engine.

    Subclasses are the only places in acadrag that emit SQL.
    """

    def __init__(self, engine: Engine):
        self.engine = engine
