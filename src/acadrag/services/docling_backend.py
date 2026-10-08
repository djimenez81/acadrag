"""Docling backend for PDF→Markdown conversion (not yet implemented)."""

from __future__ import annotations

from pathlib import Path

from acadrag.config import Config
from acadrag.services.converter import ConversionResult


class DoclingBackend:
    """Placeholder for a future Docling backend."""

    name = "docling"

    def __init__(self, cfg: Config):
        self._cfg = cfg

    def convert(self, pdf_path: Path) -> ConversionResult:
        """Raise until Docling support is implemented."""
        raise NotImplementedError("Docling backend not implemented yet")
