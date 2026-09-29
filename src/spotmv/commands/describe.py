"""spotmv describe -- set or clear a playlist's description."""

from __future__ import annotations

import argparse

import spotipy

from ..api import playlist_name
from ..errors import SpotmvError
from ..refs import LIKED_KEYS, resolve_playlist


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    describe = sub.add_parser("describe", help="set a playlist's description")
    describe.add_argument("playlist", help="playlist or alias")
    describe.add_argument(
        "description", help="the new description (pass an empty string to clear)"
    )
    return describe


def validate(args: argparse.Namespace) -> None:
    if args.playlist.strip().lower() in LIKED_KEYS:
        raise SpotmvError("Liked Songs has no editable description (it is not a playlist)")


def run(sp: spotipy.Spotify, args: argparse.Namespace) -> int:
    description = args.description
    playlist_id = resolve_playlist(args.playlist)
    name = playlist_name(sp, playlist_id)
    try:
        sp.playlist_change_details(playlist_id, description=description)
    except spotipy.SpotifyException as exc:
        if getattr(exc, "http_status", None) == 403:
            raise SpotmvError(
                f"not allowed to edit this playlist (you may not be the owner): {name}"
            ) from exc
        raise SpotmvError(f"could not update description: {exc}") from exc

    if description.strip():
        print(f"updated description for '{name}'")
    else:
        print(f"cleared description for '{name}'")
    return 0
