"""Shared pytest fixtures."""

import pytest

from acadrag.config import load_config


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    """Return a Config rooted at a fresh temporary home directory."""
    monkeypatch.setenv("ACADRAG_HOME", str(tmp_path / "home"))
    return load_config()
