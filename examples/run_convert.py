"""Run Stage 3 (convert) once against ``$ACADRAG_HOME``.

Usage::

    python examples/run_convert.py [MAX_JOBS]
"""

from __future__ import annotations

import logging
import sys

from acadrag.config import load_config
from acadrag.pipelines.convert import run_pending
from acadrag.storage.db import make_engine
from acadrag.storage.repositories import (
    DocumentRepository,
    JobRepository,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)


def main() -> None:
    """Run up to ``MAX_JOBS`` convert jobs."""
    max_jobs = int(sys.argv[1]) if len(sys.argv) > 1 else 5

    cfg = load_config()
    engine = make_engine(cfg.database.url)

    summary = run_pending(
        cfg,
        DocumentRepository(engine),
        JobRepository(engine),
        max_jobs=max_jobs,
    )
    print(summary)


if __name__ == "__main__":
    main()
