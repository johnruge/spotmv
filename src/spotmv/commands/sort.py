"""spotmv sort -- reorder a playlist by a track attribute."""

from __future__ import annotations

import argparse
from typing import Any, Dict

import spotipy

from ..api import get_all_playlist_items, item_track, playlist_name, track_artist_names
from ..backups import make_snapshot, recoverable_write, save_snapshot
from ..errors import SpotmvError
from ..refs import LIKED_KEYS, resolve_playlist
from ..targets import replace_playlist_items

SORT_KEYS = ("release", "added", "duration", "title", "artist")
DEFAULT_DESCENDING = {"release", "added"}


def _sort_key_func(key: str):
    """Return a function mapping an item to a sortable value for the given key."""

    def getter(item: Dict[str, Any]):
        track = item_track(item) or {}
        if key == "added":
            return item.get("added_at") or ""
        if key == "release":
            return (track.get("album") or {}).get("release_date") or ""
        if key == "title":
            return (track.get("name") or "").lower()
        if key == "artist":
            names = track_artist_names(track)
            return (names[0] if names else "").lower()
        if key == "duration":
            return track.get("duration_ms") or 0
        return ""

    return getter


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    srt = sub.add_parser(
        "sort",
        help="reorder a playlist by a track attribute (descending by default)",
    )
    srt.add_argument("playlist", help="playlist or alias")
    srt.add_argument(
        "--by",
        required=True,
        choices=SORT_KEYS,
        help="sort key: release date, date added, duration, title, or artist "
        "(default direction: release/added descending, duration/title/artist ascending)",
    )
    direction = srt.add_mutually_exclusive_group()
    direction.add_argument(
        "--ascending", action="store_true", help="force ascending order"
    )
    direction.add_argument(
        "--descending", action="store_true", help="force descending order"
    )
    srt.add_argument(
        "--apply", action="store_true", help="perform changes (default is dry-run)"
    )
    return srt


def validate(args: argparse.Namespace) -> None:
    if args.playlist.strip().lower() in LIKED_KEYS:
        raise SpotmvError("sort is only supported for playlists, not Liked Songs")


def run(sp: spotipy.Spotify, args: argparse.Namespace) -> int:
    playlist_id = resolve_playlist(args.playlist)
    name = playlist_name(sp, playlist_id)
    items = get_all_playlist_items(sp, playlist_id)

    if any(item_track(item) is None for item in items):
        raise SpotmvError(
            "this playlist contains unsupported items that cannot be reordered safely"
        )
    if any(
        item.get("is_local") or (item_track(item) or {}).get("is_local")
        for item in items
    ):
        raise SpotmvError(
            "sort does not support playlists containing local files "
            "(they cannot be re-added via the API)"
        )

    if args.ascending:
        descending = False
    elif args.descending:
        descending = True
    else:
        descending = args.by in DEFAULT_DESCENDING

    ordered = sorted(items, key=_sort_key_func(args.by), reverse=descending)

    direction = "descending" if descending else "ascending"

    def label(item: Dict[str, Any]) -> str:
        track = item_track(item)
        artists = ", ".join(track_artist_names(track)) or "-"
        return f"{track.get('name') or '(unknown)'} - {artists}"

    def print_summary() -> None:
        print(f"Playlist: {name} ({len(items)} tracks)")
        print(f"Sorting by {args.by}, {direction}.\n")
        preview = min(len(ordered), 15)
        for i in range(preview):
            print(f"  {i + 1:>3}. {label(ordered[i])}")
        if len(ordered) > preview:
            print(f"  ... and {len(ordered) - preview} more")

    if not args.apply:
        print("DRY RUN: no changes made\n")
        print_summary()
        return 0

    print_summary()
    print()

    # Reordering replaces the whole playlist in several calls, and a failure
    # between them (a 429, say) would leave it truncated -- so save the
    # current order first.
    backup = save_snapshot(make_snapshot(playlist_id, name, items))

    new_uris = [item_track(item)["uri"] for item in ordered]
    with recoverable_write(backup, name, "reorder playlist"):
        replace_playlist_items(sp, playlist_id, new_uris)

    print("DONE")
    print(f"  Reordered {len(new_uris)} track(s) in {name} by {args.by} ({direction}).")
    print(f"  Previous order backed up to {backup.name}")
    return 0
