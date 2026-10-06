"""Shared helpers for repositories."""

from __future__ import annotations

from sqlalchemy.engine import Engine


class BaseRepository:
    def __init__(self, engine: Engine):
        self.engine = engine
