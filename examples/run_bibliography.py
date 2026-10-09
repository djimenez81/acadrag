"""Run Stage 2 (bibliography) once against ``$ACADRAG_HOME``.

Usage::

    python examples/run_bibliography.py [MAX_JOBS]
"""

from __future__ import annotations

import logging
import sys

from acadrag.config import load_config
from acadrag.pipelines.bibliography import run_pending
from acadrag.services.grobid import GrobidClient
from acadrag.storage.db import make_engine
from acadrag.storage.repositories import (
    DocumentMetadataRepository,
    DocumentRepository,
    JobRepository,
    ReferencesRepository,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)


def main() -> None:
    """Run up to ``MAX_JOBS`` bibliography jobs."""
    max_jobs = int(sys.argv[1]) if len(sys.argv) > 1 else 10

    cfg = load_config()
    engine = make_engine(cfg.database.url)

    summary = run_pending(
        cfg,
        GrobidClient(),
        DocumentRepository(engine),
        JobRepository(engine),
        DocumentMetadataRepository(engine),
        ReferencesRepository(engine),
        max_jobs=max_jobs,
    )
    print(summary)


if __name__ == "__main__":
    main()
