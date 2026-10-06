"""YAML config loading: defaults + user overlay + environment overrides.

Resolution order (later wins):
  1. configs/default.yaml            (shipped with the package)
  2. $ACADRAG_HOME/config.yaml       (user overrides, optional)
  3. explicit `path` argument        (tests, advanced users)
Environment:
  ACADRAG_HOME overrides paths.home.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from acadrag.config.schema import Config

_PKG_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CONFIG_PATH = _PKG_ROOT / "configs" / "default.yaml"


def _deep_merge(base: dict, overlay: dict) -> dict:
    out = dict(base)
    for k, v in overlay.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _resolve_home(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    env = os.environ.get("ACADRAG_HOME")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / ".acadrag").resolve()


def load_config(
    path: Path | None = None,
    *,
    home: Path | None = None,
    create_home: bool = True,
) -> Config:
    """Load, merge, validate, and resolve acadrag's configuration."""
    merged = _read_yaml(_DEFAULT_CONFIG_PATH)

    resolved_home = _resolve_home(home)
    user_cfg_path = path or (resolved_home / "config.yaml")
    merged = _deep_merge(merged, _read_yaml(user_cfg_path))

    # Force home in, then substitute {home} placeholders in string values.
    merged.setdefault("paths", {})
    merged["paths"]["home"] = str(resolved_home)

    def _subst(obj: Any) -> Any:
        if isinstance(obj, str):
            return obj.replace("{home}", str(resolved_home))
        if isinstance(obj, dict):
            return {k: _subst(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_subst(v) for v in obj]
        return obj

    merged = _subst(merged)

    cfg = Config.model_validate(merged)
    cfg.paths = cfg.paths.resolved()

    if create_home:
        for p in (cfg.paths.home, cfg.paths.inbox, cfg.paths.processed,
                  cfg.paths.rejected, cfg.paths.logs):
            p.mkdir(parents=True, exist_ok=True)

    return cfg
