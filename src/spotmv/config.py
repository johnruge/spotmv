"""Where spotmv keeps its state, and how it finds your credentials."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from .errors import SpotmvError

# src/spotmv/config.py -> the repo root
REPO_ROOT = Path(__file__).resolve().parents[2]

CONFIG_DIR = Path(os.environ.get("SPOTMV_CONFIG_DIR", Path.home() / ".config" / "spotmv"))
ALIASES_PATH = CONFIG_DIR / "aliases.json"
CACHE_PATH = CONFIG_DIR / ".auth-cache"


# --------------------------------------------------------------------------- #
# .env loading
# --------------------------------------------------------------------------- #
def env_file_candidates() -> List[Path]:
    """Every .env worth checking, in precedence order.

    The repo's own .env comes first so the tool works from any directory. It used
    to read a bare relative "./.env", which meant the documented
    `alias spotmv="$(pwd)/spotmv"` found no credentials the moment you ran it
    from somewhere else.
    """
    candidates = [REPO_ROOT / ".env", Path.cwd() / ".env", CONFIG_DIR / ".env"]
    seen: set = set()
    unique: List[Path] = []
    for path in candidates:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


def _load_one_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs from a single file, if it exists."""
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # setdefault: a variable already exported in the shell always wins
        os.environ.setdefault(key, value)


def load_env_file(path: Optional[Path] = None) -> None:
    """Load credentials from .env. Pass a path to load exactly one file."""
    for candidate in [path] if path is not None else env_file_candidates():
        _load_one_env_file(candidate)


# --------------------------------------------------------------------------- #
# Alias store
# --------------------------------------------------------------------------- #
def load_aliases() -> Dict[str, str]:
    if not ALIASES_PATH.is_file():
        return {}
    try:
        data = json.loads(ALIASES_PATH.read_text())
    except json.JSONDecodeError as exc:
        raise SpotmvError(f"alias file is corrupt ({ALIASES_PATH}): {exc}") from exc
    if not isinstance(data, dict):
        raise SpotmvError(f"alias file has unexpected format: {ALIASES_PATH}")
    return {str(k): str(v) for k, v in data.items()}


def save_aliases(aliases: Dict[str, str]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    ALIASES_PATH.write_text(json.dumps(aliases, indent=2, sort_keys=True) + "\n")
