import pytest

from acadrag.config import load_config


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("ACADRAG_HOME", str(tmp_path / "home"))
    return load_config()
