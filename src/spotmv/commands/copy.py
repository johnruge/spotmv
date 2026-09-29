"""spotmv copy -- add tracks from one playlist to another, leaving the source alone."""

from __future__ import annotations

import argparse

import spotipy

from ..planning import by_artist, run_move


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    copy = sub.add_parser(
        "copy", help="copy tracks (optionally one artist's) into another playlist"
    )
    copy.add_argument("--source", required=True, help="source playlist, alias, or 'liked'")
    copy.add_argument("--dest", required=True, help="destination playlist, alias, or 'liked'")
    copy.add_argument("--artist", help="only copy this artist's tracks (case-insensitive)")
    copy.add_argument(
        "--apply", action="store_true", help="perform changes (default is dry-run)"
    )
    return copy


def run(sp: spotipy.Spotify, args: argparse.Namespace) -> int:
    if args.artist and args.artist.strip():
        artist = args.artist.strip()
        return run_move(
            sp, args, matches=by_artist(artist), found_label=f"Tracks by {artist} found", remove=False
        )
    return run_move(sp, args, matches=lambda track: True, found_label="Tracks found", remove=False)
