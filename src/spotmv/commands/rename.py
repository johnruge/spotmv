"""spotmv rename -- change a playlist's name."""

from __future__ import annotations

import argparse

import spotipy

from ..api import playlist_name
from ..errors import SpotmvError
from ..refs import LIKED_KEYS, resolve_playlist


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    rename = sub.add_parser("rename", help="change a playlist's name")
    rename.add_argument("playlist", help="playlist or alias")
    rename.add_argument("name", help="the new playlist name")
    return rename


def validate(args: argparse.Namespace) -> None:
    if not args.name.strip():
        raise SpotmvError("new playlist name cannot be empty")
    if args.playlist.strip().lower() in LIKED_KEYS:
        raise SpotmvError("Liked Songs cannot be renamed (it is not a playlist)")


def run(sp: spotipy.Spotify, args: argparse.Namespace) -> int:
    new_name = args.name.strip()
    playlist_id = resolve_playlist(args.playlist)
    old_name = playlist_name(sp, playlist_id)
    try:
        sp.playlist_change_details(playlist_id, name=new_name)
    except spotipy.SpotifyException as exc:
        if getattr(exc, "http_status", None) == 403:
            raise SpotmvError(
                f"not allowed to rename this playlist (you may not be the owner): {old_name}"
            ) from exc
        raise SpotmvError(f"could not rename playlist: {exc}") from exc

    print(f"renamed '{old_name}' -> '{new_name}'")
    return 0
