"""spotmv diff -- compare two playlists (or a playlist and Liked Songs)."""

from __future__ import annotations

import argparse
from typing import Any, Dict, List

import spotipy

from ..api import is_usable_track, item_track, track_artist_names
from ..errors import SpotmvError
from ..output import add_json_flag, emit
from ..refs import resolve_target
from ..targets import get_all_target_items, target_name

PREVIEW = 15


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    diff = sub.add_parser("diff", help="show which tracks two playlists do and don't share")
    diff.add_argument("a", help="playlist, alias, or 'liked'")
    diff.add_argument("b", help="playlist, alias, or 'liked'")
    add_json_flag(diff)
    return diff


def unique_tracks(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """uri -> track for every usable track, first-seen order."""
    tracks: Dict[str, Dict[str, Any]] = {}
    for item in items:
        if is_usable_track(item):
            track = item_track(item)
            tracks.setdefault(track["uri"], track)
    return tracks


def label(track: Dict[str, Any]) -> str:
    artists = ", ".join(n for n in track_artist_names(track) if n) or "-"
    return f"{track.get('name') or '(unknown)'} - {artists}"


def run(sp: spotipy.Spotify, args: argparse.Namespace) -> int:
    a, b = resolve_target(args.a), resolve_target(args.b)
    if a == b:
        raise SpotmvError("those are the same playlist")
    a_name, b_name = target_name(sp, a), target_name(sp, b)
    a_tracks = unique_tracks(get_all_target_items(sp, a))
    b_tracks = unique_tracks(get_all_target_items(sp, b))

    only_a = [t for uri, t in a_tracks.items() if uri not in b_tracks]
    only_b = [t for uri, t in b_tracks.items() if uri not in a_tracks]
    shared = len(a_tracks) - len(only_a)

    def render() -> None:
        print(f"A: {a_name} ({len(a_tracks)} unique tracks)")
        print(f"B: {b_name} ({len(b_tracks)} unique tracks)")
        print()
        print(f"  In both:     {shared}")
        print(f"  Only in A:   {len(only_a)}")
        print(f"  Only in B:   {len(only_b)}")
        for heading, tracks in ((f"Only in {a_name}", only_a), (f"Only in {b_name}", only_b)):
            if not tracks:
                continue
            print(f"\n{heading}:")
            for i, track in enumerate(tracks[:PREVIEW], start=1):
                print(f"  {i:>3}. {label(track)}")
            if len(tracks) > PREVIEW:
                print(f"  ... and {len(tracks) - PREVIEW} more")

    def as_json(track: Dict[str, Any]) -> Dict[str, Any]:
        return {"title": track.get("name") or "(unknown)", "artists": track_artist_names(track), "uri": track["uri"]}

    data = {
        "a": {"name": a_name, "unique_tracks": len(a_tracks)},
        "b": {"name": b_name, "unique_tracks": len(b_tracks)},
        "in_both": shared,
        "only_in_a": [as_json(t) for t in only_a],  # full lists, not the text preview
        "only_in_b": [as_json(t) for t in only_b],
    }
    emit(args, data, render)
    return 0
