"""Playlist snapshots: a local JSON copy of a playlist's track order.

Snapshots live in <config dir>/backups/ and are what `restore` replays. The
directory is computed on every call (never cached at import) so it always
follows config.CONFIG_DIR.
"""

from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Sequence, Tuple

import requests
import spotipy

from . import config
from .api import item_track, track_artist_names
from .errors import SpotmvError

FORMAT_VERSION = 1


def backups_dir() -> Path:
    return config.CONFIG_DIR / "backups"


def make_snapshot(playlist_id: str, name: str, items: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Capture a playlist's items, in order, as plain JSON-able data."""
    tracks = []
    for item in items:
        track = item_track(item)
        if not track or not track.get("uri"):
            continue  # nothing restorable to record
        tracks.append(
            {
                "uri": track["uri"],
                "name": track.get("name") or "",
                "artists": track_artist_names(track),
                "local": bool(item.get("is_local") or track.get("is_local")),
            }
        )
    return {
        "version": FORMAT_VERSION,
        "playlist_id": playlist_id,
        "name": name,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tracks": tracks,
    }


def save_snapshot(snapshot: Dict[str, Any]) -> Path:
    """Write a snapshot to backups/<playlist id>-<UTC timestamp>.json; never overwrites."""
    directory = backups_dir()
    directory.mkdir(parents=True, exist_ok=True)
    # "2026-09-29T12:34:56Z" -> "20260929-123456"
    stamp = snapshot["created_at"].replace("-", "").replace(":", "").replace("T", "-").rstrip("Z")
    base = f"{snapshot['playlist_id']}-{stamp}"
    path = directory / f"{base}.json"
    n = 1
    while path.exists():  # two backups in the same second
        path = directory / f"{base}-{n}.json"
        n += 1
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n")
    return path


def list_snapshots() -> List[Path]:
    directory = backups_dir()
    return sorted(directory.glob("*.json")) if directory.is_dir() else []


def load_snapshot(ref: str) -> Tuple[Path, Dict[str, Any]]:
    """Load a snapshot by path, or by bare file name inside the backups dir."""
    path = Path(ref).expanduser()
    if not path.is_file() and (backups_dir() / ref).is_file():
        path = backups_dir() / ref
    if not path.is_file():
        raise SpotmvError(f"no such backup: {ref}")
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise SpotmvError(f"could not read backup {path}: {exc}") from exc
    if not (
        isinstance(data, dict)
        and data.get("version") == FORMAT_VERSION
        and isinstance(data.get("playlist_id"), str)
        and isinstance(data.get("tracks"), list)
    ):
        raise SpotmvError(f"not a spotmv backup: {path}")
    return path, data


@contextmanager
def recoverable_write(backup: Path, name: str, action: str) -> Iterator[None]:
    """Wrap a write that takes several API calls.

    If it fails partway -- a Spotify error, a dropped connection, or Ctrl-C --
    the playlist can be left half-written, so the error ends with the exact
    command that puts it back from `backup`.
    """
    hint = (
        "\nthe playlist may now be incomplete. put it back with:\n"
        f"  spotmv restore {backup.name} --apply"
    )
    try:
        yield
    except spotipy.SpotifyException as exc:
        if getattr(exc, "http_status", None) == 403:  # refused up front: nothing changed
            raise SpotmvError(
                f"not allowed to modify this playlist (you may not be the owner): {name}"
            ) from exc
        raise SpotmvError(f"could not {action}: {exc}{hint}") from exc
    except requests.exceptions.RequestException as exc:
        raise SpotmvError(f"network problem while trying to {action}: {exc}{hint}") from exc
    except KeyboardInterrupt:
        sys.stderr.write(hint.lstrip("\n") + "\n")
        raise
