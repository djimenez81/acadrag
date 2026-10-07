"""Sharded per-document folder layout under paths.processed.

Layout:
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
    """Manages storage and rejection of documents in processed directory."""
    def __init__(self, processed_root: Path, rejected_root: Path):
        self.processed_root = processed_root
        self.rejected_root = rejected_root

    def doc_dir(self, sha256: str) -> Path:
        """Return the directory for a document with the given SHA-256 hash."""
        return self.processed_root / sha256[:2] / sha256[2:4] / sha256

    def store(self, src: Path, sha256: str) -> Path:
        """Copy `src` into its canonical sharded folder. Idempotent."""
        target = self.doc_dir(sha256) / src.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(src, target)
        return target

    def reject(self, src: Path, reason: str) -> Path:
        """Move the source file to the rejected directory with a reason."""
        target = self.rejected_root / f"{src.stem}__{reason}{src.suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(target))
        return target

    def remove_from_inbox(self, src: Path) -> None:
        """Remove the source file from the inbox if it exists."""
        src.unlink(missing_ok=True)
