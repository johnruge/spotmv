"""spotmv info -- track count, total length, owner and other details."""

from __future__ import annotations

import argparse

import spotipy

from ..api import is_usable_track, item_track
from ..output import add_json_flag, emit, format_duration
from ..refs import LIKED, resolve_target
from ..targets import get_all_target_items


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    info = sub.add_parser("info", help="show details about a playlist")
    info.add_argument("playlist", help="playlist, alias, or 'liked'")
    add_json_flag(info)
    return info


def run(sp: spotipy.Spotify, args: argparse.Namespace) -> int:
    target = resolve_target(args.playlist)
    items = get_all_target_items(sp, target)

    total_ms = sum(
        ((item_track(item) or {}).get("duration_ms") or 0) for item in items
    )
    playable = sum(1 for item in items if is_usable_track(item))

    if target == LIKED:
        liked = {"name": "Liked Songs", "tracks": len(items), "playable": playable, "duration_ms": total_ms}

        def render_liked() -> None:
            print("Liked Songs")
            print(f"  Tracks:       {len(items)}")
            print(f"  Total length: {format_duration(total_ms)}")

        emit(args, liked, render_liked)
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
    info = {
        "name": data.get("name") or "(unnamed)",
        "id": data.get("id") or target,
        "owner": owner.get("display_name") or owner.get("id") or "?",
        "owned": owner.get("id") == me_id,
        "public": bool(data.get("public")),
        "collaborative": bool(data.get("collaborative")),
        "description": data.get("description") or "",
        "followers": (data.get("followers") or {}).get("total", 0),
        "tracks": len(items),
        "playable": playable,
        "duration_ms": total_ms,
        "url": (data.get("external_urls") or {}).get("spotify") or "",
    }

    def render() -> None:
        visibility = "public" if info["public"] else "private"
        if info["collaborative"]:
            visibility += ", collaborative"
        print(f"Playlist: {info['name']}")
        print(f"  ID:           {info['id']}")
        print(f"  Owner:        {info['owner']}{' (you)' if info['owned'] else ''}")
        print(f"  Visibility:   {visibility}")
        if info["description"]:
            print(f"  Description:  {info['description']}")
        print(f"  Followers:    {info['followers']}")
        print(f"  Tracks:       {info['tracks']}")
        if playable != len(items):
            print(f"  Playable:     {playable}")
        print(f"  Total length: {format_duration(total_ms)}")
        if info["url"]:
            print(f"  URL:          {info['url']}")

    emit(args, info, render)
    return 0
