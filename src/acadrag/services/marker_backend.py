"""Marker backend for PDF→Markdown conversion."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from acadrag.config import Config
from acadrag.services.converter import ConversionResult

log = logging.getLogger(__name__)


class MarkerBackend:
    """Marker PDF→Markdown backend.

    Reads its settings from ``stages.convert.marker`` in the config.

    The ``TORCH_DEVICE`` environment variable must be set before Marker
    is imported, because Marker reads it at module load time. We set it
    in ``__init__`` and import Marker lazily in ``convert``.
    """

    name = "marker"

    def __init__(self, cfg: Config):
        self._cfg = cfg
        marker_cfg = cfg.stages.get("convert", {}).get("marker", {})
        device = cfg.stages.get("convert", {}).get("device", "cuda")

        # Marker reads TORCH_DEVICE at import time.
        existing = os.environ.get("TORCH_DEVICE")
        if existing and existing != device:
            log.warning(
                "TORCH_DEVICE was %r; overriding to %r for Marker.",
                existing,
                device,
            )
        os.environ["TORCH_DEVICE"] = device

        self._marker_cfg = marker_cfg
        self._converter = None  # lazy

    def _ensure_converter(self):
        """Import Marker and build the PdfConverter on first use."""
        if self._converter is not None:
            return

        from marker.config.parser import ConfigParser
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict

        config_dict = {
            "mode": self._marker_cfg.get("mode", "balanced"),
            "redo_inline_math": self._marker_cfg.get(
                "redo_inline_math", True
            ),
            "use_llm": self._marker_cfg.get("use_llm", False),
            "max_concurrency": self._marker_cfg.get("max_concurrency", 3),
        }

        if config_dict["use_llm"]:
            config_dict["llm_service"] = self._marker_cfg.get(
                "llm_service",
                "marker.services.ollama.OllamaService",
            )
            config_dict["ollama_base_url"] = self._marker_cfg.get(
                "ollama_base_url", "http://localhost:11434"
            )
            config_dict["ollama_model"] = self._marker_cfg.get(
                "ollama_model", "llama3.2-vision"
            )

        config_parser = ConfigParser(config_dict)
        self._converter = PdfConverter(
            config=config_parser.generate_config_dict(),
            artifact_dict=create_model_dict(),
            llm_service=config_parser.get_llm_service(),
        )

    def convert(self, pdf_path: Path) -> ConversionResult:
        """Convert ``pdf_path`` to Markdown via Marker.

        Extracted images are saved under ``<pdf_dir>/images/``.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            A :class:`ConversionResult` with Markdown and metadata.

        Raises:
            RuntimeError: If Marker is not installed or conversion
                fails.
        """
        self._ensure_converter()
        from io import BytesIO

        from marker.output import text_from_rendered

        started = time.monotonic()
        rendered = self._converter(str(pdf_path))
        text, _, images = text_from_rendered(rendered)
        duration = time.monotonic() - started

        if images:
            images_dir = pdf_path.parent / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            for filename, image_object in images.items():
                target = images_dir / filename
                fmt = target.suffix.lstrip(".").upper() or "PNG"
                if fmt == "JPG":
                    fmt = "JPEG"
                if fmt not in ("JPEG", "PNG"):
                    fmt = "PNG"
                    target = target.with_suffix(".png")
                buf = BytesIO()
                image_object.save(buf, format=fmt)
                target.write_bytes(buf.getvalue())

        metadata = dict(rendered.metadata or {})
        metadata["backend"] = "marker"
        metadata["duration_seconds"] = round(duration, 2)
        metadata["word_count"] = len(text.split())
        metadata["image_count"] = len(images) if images else 0

        return ConversionResult(markdown=text, metadata=metadata)
