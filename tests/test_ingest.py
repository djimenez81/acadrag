"""Tests for the ingest stage."""

from acadrag.pipelines.ingest import ingest_once, sha256_of
from acadrag.storage.db import make_engine
from acadrag.storage.filesystem import FileStore
from acadrag.storage.repositories.documents import DocumentRepository


def _make_repo(cfg):
    """Return (DocumentRepository, FileStore) for ``cfg``."""
    engine = make_engine(cfg.database.url)
    store = FileStore(cfg.paths.processed, cfg.paths.rejected)
    return DocumentRepository(engine), store


def test_sha256_stable(tmp_path):
    """Hashing the same file twice yields the same digest."""
    path = tmp_path / "a.txt"
    path.write_bytes(b"hello")
    assert sha256_of(path) == sha256_of(path)


def test_ingest_moves_and_records(cfg):
    """A new PDF is stored, recorded, and removed from the inbox."""
    content = b"%PDF-1.4 fake"
    src = cfg.paths.inbox / "one.pdf"
    src.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    repo, store = _make_repo(cfg)

    summary = ingest_once(cfg, repo, store)

    assert summary["processed"] == 1
    assert not src.exists()
    assert repo.count() == 1
    doc = repo.get_by_sha256(digest)
    assert doc is not None
    assert doc.stored_path.name == "original.pdf"

def test_ingest_is_idempotent(cfg):
    """Re-ingesting the same content is recorded as a duplicate."""
    src = cfg.paths.inbox / "one.pdf"
    src.write_bytes(b"%PDF-1.4 fake")
    repo, store = _make_repo(cfg)

    ingest_once(cfg, repo, store)
    (cfg.paths.inbox / "one_copy.pdf").write_bytes(b"%PDF-1.4 fake")
    summary = ingest_once(cfg, repo, store)

    assert summary["duplicates"] == 1
    assert repo.count() == 1
