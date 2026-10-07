"""Sharded per-document folder layout under ``paths.processed``.

Layout::

    processed/<h0h1>/<h2h3>/<sha256>/
        original.pdf
        document.md          (later)
        bibliography.json    (later)
        ...
"""

from __future__ import annotations

import shutil
from pathlib import Path


class FileStore:
    """Manage the on-disk layout of ingested documents.

    Args:
        processed_root: Root under which canonical document folders
            are created.
        rejected_root: Root under which rejected files are stored.
    """

    def __init__(self, processed_root: Path, rejected_root: Path):
        self.processed_root = processed_root
        self.rejected_root = rejected_root

    def doc_dir(self, sha256: str) -> Path:
        """Return the canonical directory for a document hash."""
        return self.processed_root / sha256[:2] / sha256[2:4] / sha256

    def store(self, src: Path, sha256: str) -> Path:
        """Copy ``src`` into its canonical folder as ``original.<ext>``.

        The extension is lowercased. The operation is idempotent: if
        the target already exists, it is left untouched.

        Args:
            src: Source file to copy.
            sha256: Content hash of ``src``.

        Returns:
            The path of the stored copy.
        """
        ext = src.suffix.lower()
        target = self.doc_dir(sha256) / f"original{ext}"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(src, target)
        return target

    def reject(self, src: Path, reason: str) -> Path:
        """Move ``src`` to the rejected folder, tagging it with ``reason``.

        Args:
            src: File to move.
            reason: Short tag (e.g. ``"duplicate"``) inserted in the
                resulting filename.

        Returns:
            The new path of the rejected file.
        """
        target = self.rejected_root / f"{src.stem}__{reason}{src.suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(target))
        return target

    def remove_from_inbox(self, src: Path) -> None:
        """Delete ``src`` from the inbox, ignoring a missing file."""
        src.unlink(missing_ok=True)
