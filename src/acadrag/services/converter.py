"""Converter backend protocol and factory."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from acadrag.config import Config


@dataclass
class ConversionResult:
    """Output of a successful conversion.

    Attributes:
        markdown: The converted Markdown text.
        metadata: Backend, duration, page count, word count, warnings.
    """

    markdown: str
    metadata: dict = field(default_factory=dict)


class ConverterBackend(Protocol):
    """Protocol for PDF→Markdown backends."""

    name: str

    def convert(self, pdf_path: Path) -> ConversionResult:
        """Convert a PDF to Markdown."""
        ...


def get_backend(cfg: Config, name: str) -> ConverterBackend:
    """Return a backend instance by name.

    Args:
        cfg: Loaded configuration.
        name: Backend identifier (``"marker"`` or ``"docling"``).

    Raises:
        ValueError: If ``name`` is unknown.
    """
    if name == "marker":
        from acadrag.services.marker_backend import MarkerBackend
        return MarkerBackend(cfg)
    if name == "docling":
        from acadrag.services.docling_backend import DoclingBackend
        return DoclingBackend(cfg)
    raise ValueError(f"Unknown converter backend: {name}")
