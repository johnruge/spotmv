"""spotmv restore -- put a playlist back exactly as a backup recorded it."""

from __future__ import annotations

import argparse
from typing import List

import spotipy

from ..api import get_all_playlist_items, item_track, playlist_name
from ..backups import load_snapshot
from ..errors import SpotmvError
from ..refs import parse_playlist_id
from ..targets import replace_playlist_items

RESTORABLE_PREFIXES = ("spotify:track:", "spotify:episode:")


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    restore = sub.add_parser(
        "restore", help="put a playlist back to a saved backup (see 'spotmv backups')"
    )
    restore.add_argument("backup", help="backup file name or path")
    restore.add_argument(
        "--apply", action="store_true", help="perform changes (default is dry-run)"
    )
    return restore


def unique(uris: List[str]) -> List[str]:
    return list(dict.fromkeys(uris))


def run(sp: spotipy.Spotify, args: argparse.Namespace) -> int:
    path, snapshot = load_snapshot(args.backup)
    playlist_id = parse_playlist_id(snapshot["playlist_id"])

    wanted: List[str] = []
    skipped_local = 0
    for track in snapshot["tracks"]:
        if not isinstance(track, dict):
            raise SpotmvError(f"backup has a malformed track entry: {path}")
        if track.get("local"):
            skipped_local += 1  # local files can't be re-added through the API
            continue
        uri = track.get("uri")
        if not isinstance(uri, str) or not uri.startswith(RESTORABLE_PREFIXES):
            raise SpotmvError(f"backup contains an invalid track uri: {uri!r} ({path})")
        wanted.append(uri)

    name = playlist_name(sp, playlist_id)
    items = get_all_playlist_items(sp, playlist_id)
    if any(item.get("is_local") or (item_track(item) or {}).get("is_local") for item in items):
        raise SpotmvError(
            "restore does not support playlists containing local files "
            "(replacing the track list would delete them)"
        )
    current = [(item_track(item) or {}).get("uri") for item in items]

    current_set, wanted_set = set(current), set(wanted)
    add_back = [uri for uri in unique(wanted) if uri not in current_set]
    remove = [uri for uri in unique(current) if uri not in wanted_set]
    # do the tracks on both sides sit in a different order?
    reordered = [u for u in unique(current) if u in wanted_set] != [
        u for u in unique(wanted) if u in current_set
    ]
    in_sync = current == wanted

    def print_summary() -> None:
        print(f"Playlist: {name} ({len(current)} tracks now)")
        print(f"Backup:   {path.name} ({len(wanted)} tracks, {snapshot.get('created_at') or '?'})")
        print()
        if in_sync:
            print("  Playlist already matches the backup; nothing to do.")
            return
        print(f"  Would add back: {len(add_back)}")
        print(f"  Would remove:   {len(remove)}")
        print(f"  Order:          {'changes' if reordered else 'unchanged'}")
        if skipped_local:
            print(f"  Skipped local files in backup: {skipped_local}")
        print(f"  After restore:  {len(wanted)} tracks")

    if not args.apply:
        print("DRY RUN: no changes made\n")
        print_summary()
        return 0

    print_summary()
    if in_sync:
        return 0
    print()

    try:
        replace_playlist_items(sp, playlist_id, wanted)
    except spotipy.SpotifyException as exc:
        if getattr(exc, "http_status", None) == 403:
            raise SpotmvError(
                f"not allowed to modify this playlist (you may not be the owner): {name}"
            ) from exc
        raise SpotmvError(f"could not restore playlist: {exc}") from exc

    print("DONE")
    print(f"  Restored {name} to {len(wanted)} track(s) from {path.name}.")
    return 0
