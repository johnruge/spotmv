"""spotmv backups -- list saved playlist backups."""

from __future__ import annotations

import argparse
from typing import Optional

import spotipy

from ..backups import backups_dir, list_snapshots, load_snapshot
from ..errors import SpotmvError
from ..output import render_table
from ..refs import resolve_playlist

# backups are local files; no Spotify login needed
NEEDS_CLIENT = False


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    backups = sub.add_parser("backups", help="list saved playlist backups")
    backups.add_argument(
        "playlist", nargs="?", help="only show backups of this playlist or alias"
    )
    return backups


def run(sp: Optional[spotipy.Spotify], args: argparse.Namespace) -> int:
    only = resolve_playlist(args.playlist) if args.playlist else None

    rows = []
    for path in list_snapshots():
        try:
            _, snapshot = load_snapshot(str(path))
        except SpotmvError:
            if not only:
                rows.append([path.name, "(unreadable)", "-", "-"])
            continue
        if only and snapshot["playlist_id"] != only:
            continue
        rows.append(
            [
                path.name,
                snapshot.get("name") or "(unnamed)",
                str(len(snapshot["tracks"])),
                snapshot.get("created_at") or "-",
            ]
        )

    if not rows:
        print("no backups found" + (" for that playlist" if only else ""))
        return 0
    print(render_table(["FILE", "PLAYLIST", "TRACKS", "CREATED"], rows))
    print(f"\n{len(rows)} backup(s) in {backups_dir()}")
    return 0
