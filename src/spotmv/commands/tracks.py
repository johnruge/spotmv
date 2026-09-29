"""spotmv tracks -- list a playlist's songs, who added them, and when."""

from __future__ import annotations

import argparse

import spotipy

from ..api import item_track, track_artist_names
from ..output import render_table
from ..refs import LIKED, resolve_target
from ..targets import get_all_target_items, target_name


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    tracks = sub.add_parser(
        "tracks", help="list songs in a playlist with artists, who added them, and when"
    )
    tracks.add_argument("playlist", help="playlist, alias, or 'liked'")
    return tracks


def run(sp: spotipy.Spotify, args: argparse.Namespace) -> int:
    target = resolve_target(args.playlist)
    name = target_name(sp, target)
    items = get_all_target_items(sp, target)

    me = sp.current_user()
    me_id = me.get("id")
    me_name = me.get("display_name") or me_id or "you"

    rows = []
    for index, item in enumerate(items, start=1):
        track = item_track(item)
        if not track:
            continue
        title = track.get("name") or "(unknown)"
        artists = ", ".join(n for n in track_artist_names(track) if n) or "-"
        added_at = (item.get("added_at") or "")[:10]
        if target == LIKED:
            added_by = me_name
        else:
            added_by_id = (item.get("added_by") or {}).get("id", "")
            added_by = me_name if added_by_id == me_id else (added_by_id or "-")
        rows.append([str(index), title, artists, added_by, added_at or "-"])

    print(f"{name} - {len(rows)} track(s)")
    print("(note: producer/songwriter credits are not available via the Spotify API)\n")
    print(render_table(["#", "TITLE", "ARTISTS", "ADDED BY", "ADDED"], rows))
    return 0
