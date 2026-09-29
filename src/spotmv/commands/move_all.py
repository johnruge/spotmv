"""spotmv move-all -- move every track from one playlist into another."""

from __future__ import annotations

import argparse
from typing import List

import spotipy

from ..api import is_usable_track, item_track
from ..errors import SpotmvError
from ..refs import resolve_target
from ..targets import (
    add_to_target,
    get_all_target_items,
    remove_all_from_target,
    target_name,
)


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
    source = resolve_target(args.source)
    dest = resolve_target(args.dest)
    if source == dest:
        raise SpotmvError("source and destination are the same")

    source_name = target_name(sp, source)
    dest_name = target_name(sp, dest)

    source_items = get_all_target_items(sp, source)
    dest_items = get_all_target_items(sp, dest)
    source_total = len(source_items)
    dest_total = len(dest_items)

    dest_uris = {
        item_track(item)["uri"] for item in dest_items if is_usable_track(item)
    }

    moving_uris_in_order: List[str] = []
    moving_occurrences = 0
    for item in source_items:
        if not is_usable_track(item):
            continue
        moving_occurrences += 1
        uri = item_track(item)["uri"]
        if uri not in moving_uris_in_order:
            moving_uris_in_order.append(uri)

    already_in_dest = sum(1 for uri in set(moving_uris_in_order) if uri in dest_uris)
    to_add = [uri for uri in moving_uris_in_order if uri not in dest_uris]

    predicted_source = source_total - moving_occurrences
    predicted_dest = dest_total + len(to_add)

    def print_summary() -> None:
        print(f"Source: {source_name}")
        print(f"  Current count: {source_total}")
        print(f"  Movable tracks: {moving_occurrences}")
        print(f"  Would remove from source: {moving_occurrences}")
        print(f"  Predicted source count: {predicted_source}")
        print()
        print(f"Destination: {dest_name}")
        print(f"  Current count: {dest_total}")
        print(f"  Would add to destination: {len(to_add)}")
        print(f"  Already in destination: {already_in_dest}")
        print(f"  Predicted destination count: {predicted_dest}")

    if not args.apply:
        print("DRY RUN: no changes made\n")
        print_summary()
        return 0

    print_summary()
    print()

    if not moving_uris_in_order:
        print("nothing to move.")
        return 0

    if to_add:
        add_to_target(sp, dest, to_add)
    remove_all_from_target(sp, source, moving_uris_in_order)

    print("DONE")
    print(f"  Added {len(to_add)} track(s) to {dest_name}.")
    print(f"  Removed {moving_occurrences} track(s) from {source_name}.")
    return 0
