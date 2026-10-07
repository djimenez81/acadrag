"""Run Stage 1 (ingest) once against ``$ACADRAG_HOME``.

Usage::

    python examples/run_ingest.py
"""

from __future__ import annotations

import logging

from acadrag.config import load_config
from acadrag.pipelines.ingest import ingest_once
from acadrag.storage.db import make_engine
from acadrag.storage.filesystem import FileStore
from acadrag.storage.repositories.documents import DocumentRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)


def main() -> None:
    """Load config, open the DB, and ingest the inbox once."""
    cfg = load_config()
    print(f"home      : {cfg.paths.home}")
    print(f"inbox     : {cfg.paths.inbox}")
    print(f"processed : {cfg.paths.processed}")
    print(f"db        : {cfg.database.url}")

    engine = make_engine(cfg.database.url)
    repo = DocumentRepository(engine)
    store = FileStore(cfg.paths.processed, cfg.paths.rejected)

    summary = ingest_once(cfg, repo, store)
    print(summary)


if __name__ == "__main__":
    main()
