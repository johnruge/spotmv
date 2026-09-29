"""spotmv move-all -- move every track from one playlist into another."""

from __future__ import annotations

import argparse

import spotipy

from ..planning import run_move


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    move_all = sub.add_parser(
        "move-all", help="move ALL tracks from one playlist into another"
    )
    move_all.add_argument(
        "--source", required=True, help="source playlist, alias, or 'liked'"
    )
    move_all.add_argument(
        "--dest", required=True, help="destination playlist, alias, or 'liked'"
    )
    move_all.add_argument(
        "--apply", action="store_true", help="perform changes (default is dry-run)"
    )
    return move_all


def run(sp: spotipy.Spotify, args: argparse.Namespace) -> int:
    return run_move(sp, args, matches=lambda track: True, found_label="Movable tracks")
