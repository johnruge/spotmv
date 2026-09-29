"""spotmv dupes -- find repeated tracks in a playlist and remove the extra copies."""

from __future__ import annotations

import argparse
from typing import Dict, List, Tuple

import spotipy

from ..api import BATCH_SIZE, chunked, get_all_playlist_items, is_usable_track, item_track, playlist_name, track_artist_names
from ..backups import make_snapshot, save_snapshot
from ..errors import SpotmvError
from ..refs import LIKED_KEYS, resolve_playlist


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    dupes = sub.add_parser(
        "dupes", help="find tracks that appear more than once in a playlist"
    )
    dupes.add_argument("playlist", help="playlist or alias")
    dupes.add_argument(
        "--apply",
        action="store_true",
        help="remove the extra copies, keeping the first (default is dry-run)",
    )
    return dupes


def validate(args: argparse.Namespace) -> None:
    if args.playlist.strip().lower() in LIKED_KEYS:
        raise SpotmvError("Liked Songs can't contain duplicates; dupes works on playlists")


def remove_positions(sp: spotipy.Spotify, playlist_id: str, extras: List[Tuple[str, int]]) -> None:
    """Remove the items at the given (uri, position) pairs.

    Positions are relative to the playlist as it is now, and each call shifts
    everything after what it removes -- so go from the highest position down,
    which keeps every position still to be removed valid.
    """
    for batch in chunked(sorted(extras, key=lambda pair: -pair[1]), BATCH_SIZE):
        by_uri: Dict[str, List[int]] = {}
        for uri, position in batch:
            by_uri.setdefault(uri, []).append(position)
        sp.playlist_remove_specific_occurrences_of_items(
            playlist_id, [{"uri": uri, "positions": positions} for uri, positions in by_uri.items()]
        )


def run(sp: spotipy.Spotify, args: argparse.Namespace) -> int:
    playlist_id = resolve_playlist(args.playlist)
    name = playlist_name(sp, playlist_id)
    items = get_all_playlist_items(sp, playlist_id)

    first_seen: Dict[str, int] = {}
    copies: Dict[str, int] = {}
    labels: Dict[str, str] = {}
    extras: List[Tuple[str, int]] = []  # every copy after the first, with its position
    for position, item in enumerate(items):
        if not is_usable_track(item):
            continue
        track = item_track(item)
        uri = track["uri"]
        copies[uri] = copies.get(uri, 0) + 1
        if uri in first_seen:
            extras.append((uri, position))
        else:
            first_seen[uri] = position
            artists = ", ".join(n for n in track_artist_names(track) if n) or "-"
            labels[uri] = f"{track.get('name') or '(unknown)'} - {artists}"
    repeated = [uri for uri in first_seen if copies[uri] > 1]

    def print_summary() -> None:
        print(f"Playlist: {name} ({len(items)} tracks)\n")
        if not repeated:
            print("  No duplicates found.")
            return
        preview = repeated[:15]
        for uri in preview:
            print(f"  {labels[uri]}: {copies[uri]} copies")
        if len(repeated) > len(preview):
            print(f"  ... and {len(repeated) - len(preview)} more")
        print()
        print(f"  Tracks with duplicates: {len(repeated)}")
        print(f"  Extra copies to remove: {len(extras)} (the first copy stays where it is)")
        print(f"  Predicted count: {len(items) - len(extras)}")

    if not args.apply:
        print("DRY RUN: no changes made\n")
        print_summary()
        return 0

    print_summary()
    if not extras:
        return 0
    print()

    backup = save_snapshot(make_snapshot(playlist_id, name, items))
    try:
        remove_positions(sp, playlist_id, extras)
    except spotipy.SpotifyException as exc:
        if getattr(exc, "http_status", None) == 403:
            raise SpotmvError(
                f"not allowed to modify this playlist (you may not be the owner): {name}"
            ) from exc
        raise SpotmvError(
            f"could not remove duplicates: {exc}\n"
            "some copies may already be gone. put it back with:\n"
            f"  spotmv restore {backup.name} --apply"
        ) from exc

    print("DONE")
    print(f"  Removed {len(extras)} extra cop{'y' if len(extras) == 1 else 'ies'} from {name}.")
    print(f"  Previous version backed up to {backup.name}")
    return 0
