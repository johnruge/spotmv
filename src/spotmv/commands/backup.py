"""spotmv backup -- save a playlist's track order to a local file."""

from __future__ import annotations

import argparse

import spotipy

from ..api import get_all_playlist_items, playlist_name
from ..backups import make_snapshot, save_snapshot
from ..errors import SpotmvError
from ..refs import LIKED_KEYS, resolve_playlist


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    backup = sub.add_parser("backup", help="save a playlist's tracks to a local JSON file")
    backup.add_argument("playlist", help="playlist or alias")
    return backup


def validate(args: argparse.Namespace) -> None:
    if args.playlist.strip().lower() in LIKED_KEYS:
        raise SpotmvError("backup is only supported for playlists, not Liked Songs")


def run(sp: spotipy.Spotify, args: argparse.Namespace) -> int:
    playlist_id = resolve_playlist(args.playlist)
    name = playlist_name(sp, playlist_id)
    snapshot = make_snapshot(playlist_id, name, get_all_playlist_items(sp, playlist_id))
    path = save_snapshot(snapshot)
    print(f"backed up {len(snapshot['tracks'])} track(s) from '{name}'")
    print(f"  {path}")
    return 0
