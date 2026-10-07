"""YAML config loading: defaults + user overlay + environment overrides.

Resolution order (later wins):

1. ``src/acadrag/configs/default.yaml``  (shipped with the package)
2. ``$ACADRAG_HOME/config.yaml``          (user overrides, optional)
3. explicit ``path`` argument             (tests, advanced users)

Environment:

* ``ACADRAG_HOME`` overrides ``paths.home``.
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
    """Recursively merge ``overlay`` into ``base`` (overlay wins).

    Args:
        base: Base mapping; not modified.
        overlay: Mapping whose values take precedence.

    Returns:
        A new mapping.
    """
    out = dict(base)
    for key, value in overlay.items():
        if (
            key in out
            and isinstance(out[key], dict)
            and isinstance(value, dict)
        ):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _read_yaml(path: Path) -> dict[str, Any]:
    """Return the parsed YAML at ``path``, or ``{}`` if it is absent."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _resolve_home(explicit: Path | None) -> Path:
    """Resolve the acadrag home directory.

    Precedence: explicit argument, then ``$ACADRAG_HOME``, then
    ``~/.acadrag``.
    """
    if explicit is not None:
        return explicit.expanduser().resolve()
    env = os.environ.get("ACADRAG_HOME")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / ".acadrag").resolve()


def _substitute_home(obj: Any, home: Path) -> Any:
    """Recursively replace the literal ``{home}`` in every string."""
    if isinstance(obj, str):
        return obj.replace("{home}", str(home))
    if isinstance(obj, dict):
        return {k: _substitute_home(v, home) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute_home(v, home) for v in obj]
    return obj


def load_config(
    path: Path | None = None,
    *,
    home: Path | None = None,
    create_home: bool = True,
) -> Config:
    """Load, merge, validate, and resolve acadrag's configuration.

    Args:
        path: Optional explicit user config path. Defaults to
            ``$ACADRAG_HOME/config.yaml``.
        home: Optional explicit home directory. Overrides
            ``$ACADRAG_HOME``.
        create_home: If True, create the home directory and its
            standard subdirectories if they do not exist.

    Returns:
        A fully validated and path-resolved :class:`Config`.
    """
    merged = _read_yaml(_DEFAULT_CONFIG_PATH)

    resolved_home = _resolve_home(home)
    user_cfg_path = path or (resolved_home / "config.yaml")
    merged = _deep_merge(merged, _read_yaml(user_cfg_path))

    # Force home in, then substitute ``{home}`` placeholders.
    merged.setdefault("paths", {})
    merged["paths"]["home"] = str(resolved_home)
    merged = _substitute_home(merged, resolved_home)

    cfg = Config.model_validate(merged)
    cfg.paths = cfg.paths.resolved()

    if create_home:
        for p in (
            cfg.paths.home,
            cfg.paths.inbox,
            cfg.paths.processed,
            cfg.paths.rejected,
            cfg.paths.logs,
        ):
            p.mkdir(parents=True, exist_ok=True)

    return cfg
