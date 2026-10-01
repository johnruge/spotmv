"""spotmv collect-artist -- gather an artist from every playlist you own into one."""

from __future__ import annotations

import argparse
from typing import Any, Dict, List, Tuple

import spotipy

from ..api import get_all_playlist_items, get_all_playlists, playlist_name
from ..planning import MovePlan, by_artist, plan_move
from ..refs import resolve_playlist
from ..targets import add_to_target, remove_all_from_target


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    collect = sub.add_parser(
        "collect-artist",
        help="move an artist's tracks from ALL playlists you own into one playlist",
    )
    collect.add_argument("--dest", required=True, help="destination playlist or alias")
    collect.add_argument("--artist", required=True, help="artist name (case-insensitive)")
    collect.add_argument(
        "--apply", action="store_true", help="perform changes (default is dry-run)"
    )
    return collect


def run(sp: spotipy.Spotify, args: argparse.Namespace) -> int:
    dest_id = resolve_playlist(args.dest)
    artist = args.artist.strip()
    matches = by_artist(artist)

    me_id = sp.current_user().get("id")
    owned = [
        pl
        for pl in get_all_playlists(sp)
        if (pl.get("owner") or {}).get("id") == me_id and pl.get("id") != dest_id
    ]

    dest_name = playlist_name(sp, dest_id)
    dest_items = get_all_playlist_items(sp, dest_id)

    # one plan per source playlist (what to remove from it), and one overall
    # plan across all of them (what the destination is missing)
    sources: List[Tuple[str, str, MovePlan]] = []
    matching_items: List[Dict[str, Any]] = []
    for pl in owned:
        items = get_all_playlist_items(sp, pl.get("id"))
        plan = plan_move(items, [], matches)
        if plan.occurrences:
            sources.append((pl.get("name") or "(unnamed)", pl.get("id"), plan))
            matching_items.extend(items)
    overall = plan_move(matching_items, dest_items, matches)

    def print_summary() -> None:
        print(f"Artist: {artist}")
        print(f"Destination: {dest_name} (current count: {overall.dest_total})")
        print(
            f"Scanned {len(owned)} owned playlist(s); "
            f"{len(sources)} with matching tracks.\n"
        )
        for name, _, plan in sources:
            print(f"  {name}: found {plan.occurrences}, "
                  f"would remove {plan.occurrences}")
        if sources:
            print()
        print(f"  Total matching occurrences across sources: {overall.occurrences}")
        print(f"  Unique tracks: {len(overall.uris)}")
        print(f"  Already in destination: {overall.already_in_dest}")
        print(f"  Would add to destination: {len(overall.to_add)}")
        print(f"  Predicted destination count: {overall.predicted_dest}")

    if not args.apply:
        print("DRY RUN: no changes made\n")
        print_summary()
        return 0

    print_summary()
    print()

    if not overall.uris:
        print("nothing to move.")
        return 0

    if overall.to_add:
        add_to_target(sp, dest_id, overall.to_add)
    for _, source_id, plan in sources:
        remove_all_from_target(sp, source_id, plan.uris)

    print("DONE")
    print(f"  Added {len(overall.to_add)} track(s) to {dest_name}.")
    print(f"  Removed {overall.occurrences} track(s) across {len(sources)} playlist(s).")
    return 0
