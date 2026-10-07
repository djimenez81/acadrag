from pathlib import Path

from acadrag.pipelines.ingest import ingest_once, sha256_of
from acadrag.storage.db import make_engine
from acadrag.storage.filesystem import FileStore
from acadrag.storage.repositories.documents import DocumentRepository


def _make_repo(cfg):
    engine = make_engine(cfg.database.url)
    return DocumentRepository(engine), FileStore(cfg.paths.processed, cfg.paths.rejected)


def test_sha256_stable(tmp_path):
    p = tmp_path / "a.txt"
    p.write_bytes(b"hello")
    assert sha256_of(p) == sha256_of(p)


def test_ingest_moves_and_records(cfg):
    src = cfg.paths.inbox / "one.pdf"
    src.write_bytes(b"%PDF-1.4 fake")
    repo, store = _make_repo(cfg)

    summary = ingest_once(cfg, repo, store)
    assert summary["processed"] == 1
    assert not src.exists()
    assert repo.count() == 1


def test_ingest_is_idempotent(cfg):
    src = cfg.paths.inbox / "one.pdf"
    src.write_bytes(b"%PDF-1.4 fake")
    repo, store = _make_repo(cfg)

    ingest_once(cfg, repo, store)
    # Drop an identical file back into the inbox.
    (cfg.paths.inbox / "one_copy.pdf").write_bytes(b"%PDF-1.4 fake")
    summary = ingest_once(cfg, repo, store)
    assert summary["duplicates"] == 1
    assert repo.count() == 1
