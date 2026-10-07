"""Pydantic models describing acadrag's configuration.

The schema is *grown* as stages are implemented: a key is added here
only when the code that reads it exists. See
``src/acadrag/configs/default.yaml`` for the currently-supported
surface.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class PathsConfig(BaseModel):
    """Filesystem locations used by acadrag.

    All non-``home`` fields may be absolute or relative. If relative,
    they are resolved against ``home`` by :meth:`resolved`.
    """

    home: Path | None = None
    inbox: Path = Path("inbox")
    processed: Path = Path("processed")
    rejected: Path = Path("rejected")
    logs: Path = Path("logs")

    def resolved(self) -> "PathsConfig":
        """Return a copy with relative paths resolved against ``home``.

        The receiver is not modified.

        Raises:
            ValueError: If ``home`` is not set.
        """
        if self.home is None:
            raise ValueError("paths.home must be set before resolving")
        home = self.home

        def _abs(p: Path) -> Path:
            return p if p.is_absolute() else home / p

        return PathsConfig(
            home=home,
            inbox=_abs(self.inbox),
            processed=_abs(self.processed),
            rejected=_abs(self.rejected),
            logs=_abs(self.logs),
        )


class DatabaseConfig(BaseModel):
    """Database connection settings."""

    url: str


class Config(BaseModel):
    """Top-level acadrag configuration.

    Extra sections (``models``, ``stages``, ``taxonomies``,
    ``classifiers``) are kept as opaque dicts for now and will be
    promoted to typed sub-models as their consumers are implemented.
    """

    paths: PathsConfig
    database: DatabaseConfig
    models: dict = Field(default_factory=dict)
    stages: dict = Field(default_factory=dict)
    taxonomies: dict = Field(default_factory=dict)
    classifiers: dict = Field(default_factory=dict)
