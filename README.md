# acadrag

An enhanced academic RAG pipeline for PDF corpora.

## Install (editable)

    pip install -e ".[dev]"

## First run

Set ACADRAG_HOME (optional; defaults to ~/.acadrag):

    export ACADRAG_HOME=/path/to/my/acadrag_data

Then in Python:

    from acadrag.config import load_config
    cfg = load_config()
    print(cfg.paths.home)

See `configs/user.example.yaml` for the override file format.
