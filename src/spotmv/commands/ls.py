"""spotmv ls -- list every playlist you can access."""

from __future__ import annotations

import argparse

import spotipy

from ..api import get_all_playlists
from ..output import add_json_flag, emit, render_table


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    ls = sub.add_parser("ls", help="list playlists accessible to you")
    add_json_flag(ls)
    return ls


def run(sp: spotipy.Spotify, args: argparse.Namespace) -> int:
    me_id = sp.current_user().get("id")
    playlists = get_all_playlists(sp)

    data = []
    for pl in playlists:
        owner = pl.get("owner") or {}
        data.append(
            {
                "name": pl.get("name") or "(unnamed)",
                "id": pl.get("id") or "",
                "owner": owner.get("display_name") or owner.get("id") or "",
                "owned": owner.get("id") == me_id,
            }
        )

    def render() -> None:
        rows = [[d["name"], d["id"], d["owner"], "yes" if d["owned"] else "no"] for d in data]
        print(render_table(["NAME", "ID", "OWNER", "OWNED"], rows))
        print(f"\n{len(rows)} playlist(s) (use 'spotmv info <playlist>' for track counts)")

    emit(args, data, render)
    return 0
