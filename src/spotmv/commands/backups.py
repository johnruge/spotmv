"""spotmv backups -- list saved playlist backups."""

from __future__ import annotations

import argparse
from typing import Optional

import spotipy

from ..backups import backups_dir, list_snapshots, load_snapshot
from ..errors import SpotmvError
from ..output import add_json_flag, emit, render_table
from ..refs import resolve_playlist

# backups are local files; no Spotify login needed
NEEDS_CLIENT = False


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    backups = sub.add_parser("backups", help="list saved playlist backups")
    backups.add_argument(
        "playlist", nargs="?", help="only show backups of this playlist or alias"
    )
    add_json_flag(backups)
    return backups


def run(sp: Optional[spotipy.Spotify], args: argparse.Namespace) -> int:
    only = resolve_playlist(args.playlist) if args.playlist else None

    found = []
    for path in list_snapshots():
        try:
            _, snapshot = load_snapshot(str(path))
        except SpotmvError:
            if not only:
                found.append({"file": path.name, "path": str(path), "readable": False})
            continue
        if only and snapshot["playlist_id"] != only:
            continue
        found.append(
            {
                "file": path.name,
                "path": str(path),
                "readable": True,
                "playlist": snapshot.get("name") or "(unnamed)",
                "playlist_id": snapshot["playlist_id"],
                "tracks": len(snapshot["tracks"]),
                "created_at": snapshot.get("created_at") or "",
            }
        )

    def render() -> None:
        if not found:
            print("no backups found" + (" for that playlist" if only else ""))
            return
        rows = [
            [b["file"], b["playlist"], str(b["tracks"]), b["created_at"] or "-"]
            if b["readable"]
            else [b["file"], "(unreadable)", "-", "-"]
            for b in found
        ]
        print(render_table(["FILE", "PLAYLIST", "TRACKS", "CREATED"], rows))
        print(f"\n{len(rows)} backup(s) in {backups_dir()}")

    emit(args, found, render)
    return 0
