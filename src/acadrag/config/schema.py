"""Pydantic models describing acadrag's configuration.

The schema is *grown* as stages are implemented: a key is added here only
when the code that reads it exists. See `configs/default.yaml` for the
currently-supported surface.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class PathsConfig(BaseModel):
    """Configuration settings for file paths."""
    home: Path | None = None
    inbox: Path = Path("inbox")
    processed: Path = Path("processed")
    rejected: Path = Path("rejected")
    logs: Path = Path("logs")

    def resolved(self) -> "PathsConfig":
        """Return a copy with all relative paths resolved against `home`."""
        if self.home is None:
            raise ValueError("paths.home must be set before resolving")
        home = self.home
        return PathsConfig(
            home=home,
            inbox=(
                home / self.inbox
                if not self.inbox.is_absolute()
                else self.inbox
            ),
            processed=(
                home / self.processed
                if not self.processed.is_absolute()
                else self.processed
            ),
            rejected=(
                home / self.rejected
                if not self.rejected.is_absolute()
                else self.rejected
            ),
            logs=(
                home / self.logs
                if not self.logs.is_absolute()
                else self.logs
            ),
        )


class DatabaseConfig(BaseModel):
    """Configuration settings for the database."""
    url: str


class Config(BaseModel):
    """Top-level configuration model that aggregates other configurations."""
    paths: PathsConfig
    database: DatabaseConfig
    models: dict = Field(default_factory=dict)
    stages: dict = Field(default_factory=dict)
    taxonomies: dict = Field(default_factory=dict)
    classifiers: dict = Field(default_factory=dict)
