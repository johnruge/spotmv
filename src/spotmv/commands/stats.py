"""spotmv stats -- what's in a playlist: length, top artists, decades."""

from __future__ import annotations

import argparse
from collections import Counter
from typing import Any, Dict

import spotipy

from ..api import is_usable_track, item_track, track_artist_names
from ..output import add_json_flag, emit, format_duration
from ..refs import resolve_target
from ..targets import get_all_target_items, target_name

TOP_ARTISTS = 10


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    stats = sub.add_parser("stats", help="top artists, decades and length of a playlist")
    stats.add_argument("playlist", help="playlist, alias, or 'liked'")
    add_json_flag(stats)
    return stats


def decade(track: Dict[str, Any]) -> str:
    year = ((track.get("album") or {}).get("release_date") or "")[:4]
    return f"{int(year) // 10 * 10}s" if year.isdigit() else "unknown"


def run(sp: spotipy.Spotify, args: argparse.Namespace) -> int:
    target = resolve_target(args.playlist)
    name = target_name(sp, target)
    items = get_all_target_items(sp, target)
    # same items `info` counts, so the totals agree between the two commands
    tracks = [track for track in (item_track(item) for item in items) if track]

    total_ms = sum(track.get("duration_ms") or 0 for track in tracks)
    timed = sum(1 for track in tracks if track.get("duration_ms"))
    artists = Counter(n for track in tracks for n in set(track_artist_names(track)) if n)
    decades = Counter(decade(track) for track in tracks)
    decade_order = sorted(decades, key=lambda d: (d == "unknown", d))

    data = {
        "name": name,
        "tracks": len(items),
        "playable": sum(1 for item in items if is_usable_track(item)),
        "duration_ms": total_ms,
        "average_ms": total_ms // timed if timed else 0,
        "distinct_artists": len(artists),
        "artists": [{"artist": a, "tracks": n} for a, n in sorted(artists.items(), key=lambda kv: (-kv[1], kv[0].lower()))],
        "decades": {d: decades[d] for d in decade_order},
    }

    def render() -> None:
        print(f"Stats: {name}\n")
        print(f"  Tracks:           {data['tracks']}")
        if data["playable"] != data["tracks"]:
            print(f"  Playable:         {data['playable']}")
        print(f"  Total length:     {format_duration(total_ms)}")
        print(f"  Average length:   {format_duration(data['average_ms'])}")
        print(f"  Distinct artists: {data['distinct_artists']}")
        if data["artists"]:
            print("\nTop artists:")
            top = data["artists"][:TOP_ARTISTS]
            width = max(len(a["artist"]) for a in top)
            for i, a in enumerate(top, start=1):
                print(f"  {i:>3}. {a['artist'].ljust(width)}  {a['tracks']}")
        if decades:
            print("\nRelease decades:")
            for d in decade_order:
                share = round(100 * decades[d] / len(tracks))
                print(f"  {d:<8} {decades[d]:>4}  ({share}%)")

    emit(args, data, render)
    return 0
