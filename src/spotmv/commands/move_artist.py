"""spotmv move-artist -- move one artist's tracks between playlists / Liked Songs."""

from __future__ import annotations

import argparse

import spotipy

from ..planning import by_artist, run_move


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    move = sub.add_parser("move-artist", help="move an artist's tracks between playlists")
    move.add_argument(
        "--source", required=True, help="source playlist, alias, or 'liked'"
    )
    move.add_argument(
        "--dest", required=True, help="destination playlist, alias, or 'liked'"
    )
    move.add_argument("--artist", required=True, help="artist name (case-insensitive)")
    move.add_argument(
        "--apply", action="store_true", help="perform changes (default is dry-run)"
    )
    return move


def run(sp: spotipy.Spotify, args: argparse.Namespace) -> int:
    artist = args.artist.strip()
    return run_move(sp, args, matches=by_artist(artist), found_label=f"Tracks by {artist} found")
