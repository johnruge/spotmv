"""spotmv find -- which of your playlists contain a song or artist?"""

from __future__ import annotations

import argparse
from typing import Any, Dict, List, Tuple

import spotipy

from ..api import (
    get_all_playlist_items,
    get_all_playlists,
    get_all_saved_tracks,
    is_usable_track,
    item_track,
    track_artist_names,
)
from ..errors import SpotmvError
from ..output import render_table


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    find = sub.add_parser(
        "find", help="search your playlists and Liked Songs by title or artist"
    )
    find.add_argument("query", help="text to look for (case-insensitive)")
    return find


def validate(args: argparse.Namespace) -> None:
    if not args.query.strip():
        raise SpotmvError("search query cannot be empty")


def matches(track: Dict[str, Any], needle: str) -> bool:
    names = [track.get("name") or ""] + track_artist_names(track)
    return any(needle in name.lower() for name in names)


def run(sp: spotipy.Spotify, args: argparse.Namespace) -> int:
    needle = args.query.strip().lower()

    me_id = sp.current_user().get("id")
    owned = [pl for pl in get_all_playlists(sp) if (pl.get("owner") or {}).get("id") == me_id]
    places: List[Tuple[str, List[Dict[str, Any]]]] = [
        (pl.get("name") or "(unnamed)", get_all_playlist_items(sp, pl.get("id")))
        for pl in owned
    ]
    places.append(("Liked Songs", get_all_saved_tracks(sp)))

    rows = []
    found_in = set()
    for place, items in places:
        seen = set()  # list a track once per playlist, even if it's in there twice
        for item in items:
            if not is_usable_track(item):
                continue
            track = item_track(item)
            if track["uri"] in seen or not matches(track, needle):
                continue
            seen.add(track["uri"])
            found_in.add(place)
            artists = ", ".join(n for n in track_artist_names(track) if n) or "-"
            rows.append([track.get("name") or "(unknown)", artists, place])

    print(f'Searched {len(owned)} owned playlist(s) and Liked Songs for "{args.query.strip()}".\n')
    if not rows:
        print("no matches")
        return 0
    print(render_table(["TITLE", "ARTISTS", "PLAYLIST"], rows))
    print(f"\n{len(rows)} match(es) across {len(found_in)} playlist(s)")
    return 0
