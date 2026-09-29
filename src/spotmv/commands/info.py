"""spotmv info -- track count, total length, owner and other details."""

from __future__ import annotations

import argparse

import spotipy

from ..api import is_usable_track, item_track
from ..output import format_duration
from ..refs import LIKED, resolve_target
from ..targets import get_all_target_items


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    info = sub.add_parser("info", help="show details about a playlist")
    info.add_argument("playlist", help="playlist, alias, or 'liked'")
    return info


def run(sp: spotipy.Spotify, args: argparse.Namespace) -> int:
    target = resolve_target(args.playlist)
    items = get_all_target_items(sp, target)

    total_ms = sum(
        ((item_track(item) or {}).get("duration_ms") or 0) for item in items
    )
    playable = sum(1 for item in items if is_usable_track(item))

    if target == LIKED:
        print("Liked Songs")
        print(f"  Tracks:       {len(items)}")
        print(f"  Total length: {format_duration(total_ms)}")
        return 0

    data = sp.playlist(
        target,
        fields=(
            "name,description,public,collaborative,id,"
            "owner.display_name,owner.id,followers.total,external_urls.spotify"
        ),
    )
    me_id = sp.current_user().get("id")
    owner = data.get("owner") or {}
    owned = owner.get("id") == me_id

    visibility = "public" if data.get("public") else "private"
    if data.get("collaborative"):
        visibility += ", collaborative"

    print(f"Playlist: {data.get('name') or '(unnamed)'}")
    print(f"  ID:           {data.get('id') or target}")
    owner_label = owner.get("display_name") or owner.get("id") or "?"
    print(f"  Owner:        {owner_label}{' (you)' if owned else ''}")
    print(f"  Visibility:   {visibility}")
    if data.get("description"):
        print(f"  Description:  {data['description']}")
    print(f"  Followers:    {(data.get('followers') or {}).get('total', 0)}")
    print(f"  Tracks:       {len(items)}")
    if playable != len(items):
        print(f"  Playable:     {playable}")
    print(f"  Total length: {format_duration(total_ms)}")
    url = (data.get("external_urls") or {}).get("spotify")
    if url:
        print(f"  URL:          {url}")
    return 0
