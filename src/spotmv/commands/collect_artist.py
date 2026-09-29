"""spotmv collect-artist -- gather an artist from every playlist you own into one."""

from __future__ import annotations

import argparse
from typing import Any, Dict, List

import spotipy

from ..api import (
    chunked,
    get_all_playlist_items,
    get_all_playlists,
    is_usable_track,
    item_track,
    playlist_name,
    track_artist_names,
)
from ..refs import resolve_playlist


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
    artist_key = artist.lower()

    me_id = sp.current_user().get("id")
    owned = [
        pl
        for pl in get_all_playlists(sp)
        if (pl.get("owner") or {}).get("id") == me_id and pl.get("id") != dest_id
    ]

    dest_name = playlist_name(sp, dest_id)
    dest_items = get_all_playlist_items(sp, dest_id)
    dest_total = len(dest_items)
    dest_uris = {
        item_track(item)["uri"] for item in dest_items if is_usable_track(item)
    }

    sources: List[Dict[str, Any]] = []
    total_occurrences = 0
    collected_order: List[str] = []
    collected_seen: set[str] = set()

    for pl in owned:
        pid = pl.get("id")
        occurrences = 0
        uris_here: List[str] = []
        seen_here: set[str] = set()
        for item in get_all_playlist_items(sp, pid):
            if not is_usable_track(item):
                continue
            track = item_track(item)
            if any(name.lower() == artist_key for name in track_artist_names(track)):
                occurrences += 1
                uri = track["uri"]
                if uri not in seen_here:
                    seen_here.add(uri)
                    uris_here.append(uri)
                if uri not in collected_seen:
                    collected_seen.add(uri)
                    collected_order.append(uri)
        if occurrences:
            sources.append(
                {
                    "name": pl.get("name") or "(unnamed)",
                    "id": pid,
                    "occurrences": occurrences,
                    "uris": uris_here,
                }
            )
            total_occurrences += occurrences

    already_in_dest = sum(1 for uri in collected_order if uri in dest_uris)
    to_add = [uri for uri in collected_order if uri not in dest_uris]
    predicted_dest = dest_total + len(to_add)

    def print_summary() -> None:
        print(f"Artist: {artist}")
        print(f"Destination: {dest_name} (current count: {dest_total})")
        print(
            f"Scanned {len(owned)} owned playlist(s); "
            f"{len(sources)} with matching tracks.\n"
        )
        for src in sources:
            print(f"  {src['name']}: found {src['occurrences']}, "
                  f"would remove {src['occurrences']}")
        if sources:
            print()
        print(f"  Total matching occurrences across sources: {total_occurrences}")
        print(f"  Unique tracks: {len(collected_order)}")
        print(f"  Already in destination: {already_in_dest}")
        print(f"  Would add to destination: {len(to_add)}")
        print(f"  Predicted destination count: {predicted_dest}")

    if not args.apply:
        print("DRY RUN: no changes made\n")
        print_summary()
        return 0

    print_summary()
    print()

    if not collected_order:
        print("nothing to move.")
        return 0

    if to_add:
        for batch in chunked(to_add):
            sp.playlist_add_items(dest_id, batch)

    removed_total = 0
    for src in sources:
        for batch in chunked(src["uris"]):
            sp.playlist_remove_all_occurrences_of_items(src["id"], batch)
        removed_total += src["occurrences"]

    print("DONE")
    print(f"  Added {len(to_add)} track(s) to {dest_name}.")
    print(f"  Removed {removed_total} track(s) across {len(sources)} playlist(s).")
    return 0
