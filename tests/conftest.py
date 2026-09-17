"""Shared test setup.

Two autouse fixtures keep the suite hermetic:

* ``isolated_config`` points every config path at a tmp dir, so no test can read
  or write the real ``~/.config/spotmv/``.
* ``no_network`` replaces ``get_client`` with a raiser, so a test that forgets to
  inject a :class:`FakeSpotify` fails loudly instead of calling the live API.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Modules that may own the config constants / get_client as the refactor moves
# code around. Each is patched only if it exists and defines the name.
_CONFIG_HOMES = ("spotmv.config", "spotmv.cli")
_CLIENT_HOMES = ("spotmv.auth", "spotmv.cli")


def _try_import(name: str):
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch) -> Path:
    """Redirect CONFIG_DIR (and the paths derived from it) into tmp_path."""
    config_dir = tmp_path / "spotmv-config"
    config_dir.mkdir()
    monkeypatch.setenv("SPOTMV_CONFIG_DIR", str(config_dir))

    patched = False
    for name in _CONFIG_HOMES:
        module = _try_import(name)
        if module is None or not hasattr(module, "CONFIG_DIR"):
            continue
        monkeypatch.setattr(module, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(module, "ALIASES_PATH", config_dir / "aliases.json")
        monkeypatch.setattr(module, "CACHE_PATH", config_dir / ".auth-cache")
        patched = True

    assert patched, f"no module among {_CONFIG_HOMES} defines CONFIG_DIR"
    return config_dir


@pytest.fixture(autouse=True)
def no_network(monkeypatch) -> None:
    """Make any un-injected call to the real Spotify client an immediate failure."""

    def _forbidden(*args, **kwargs):
        raise AssertionError(
            "get_client() was called during a test; pass a FakeSpotify instead"
        )

    patched = False
    for name in _CLIENT_HOMES:
        module = _try_import(name)
        if module is None or not hasattr(module, "get_client"):
            continue
        monkeypatch.setattr(module, "get_client", _forbidden)
        patched = True

    assert patched, f"no module among {_CLIENT_HOMES} defines get_client"


@pytest.fixture
def cli_module():
    """The CLI module, imported lazily so path setup above has already run."""
    return importlib.import_module("spotmv.cli")


def find_subparsers(parser) -> Optional[dict]:
    """Return the subcommand name -> parser mapping of an argparse parser."""
    for action in parser._actions:  # noqa: SLF001 - argparse exposes no public API
        if hasattr(action, "choices") and isinstance(action.choices, dict):
            return action.choices
    return None
