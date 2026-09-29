"""spotmv ls -- list every playlist you can access."""

from __future__ import annotations

import argparse

import spotipy

from ..api import get_all_playlists
from ..output import render_table


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    return sub.add_parser("ls", help="list playlists accessible to you")


def run(sp: spotipy.Spotify, args: argparse.Namespace) -> int:
    me_id = sp.current_user().get("id")
    playlists = get_all_playlists(sp)

    rows = []
    for pl in playlists:
        owner = pl.get("owner") or {}
        owned = owner.get("id") == me_id
        rows.append(
            [
                pl.get("name") or "(unnamed)",
                pl.get("id") or "",
                owner.get("display_name") or owner.get("id") or "",
                "yes" if owned else "no",
            ]
        )

    headers = ["NAME", "ID", "OWNER", "OWNED"]
    print(render_table(headers, rows))
    print(f"\n{len(rows)} playlist(s) (use 'spotmv info <playlist>' for track counts)")
    return 0
