"""spotmv alias -- name playlists so you don't paste ids/urls repeatedly."""

from __future__ import annotations

import argparse
from typing import Optional

import spotipy

from ..config import load_aliases, save_aliases
from ..errors import SpotmvError
from ..output import add_json_flag, emit, render_table
from ..refs import parse_playlist_id, resolve_playlist

# aliases live in a local file; no Spotify login needed
NEEDS_CLIENT = False


def register(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    alias = sub.add_parser("alias", help="manage playlist aliases")
    alias_sub = alias.add_subparsers(dest="alias_cmd", required=True)
    p_add = alias_sub.add_parser("add", help="add an alias")
    p_add.add_argument("name")
    p_add.add_argument("target", help="playlist id, url, or spotify:playlist: uri")
    p_rm = alias_sub.add_parser("rm", help="remove an alias")
    p_rm.add_argument("name")
    add_json_flag(alias_sub.add_parser("ls", help="list aliases"))
    p_res = alias_sub.add_parser("resolve", help="print the id an alias resolves to")
    p_res.add_argument("name")
    return alias


def run(sp: Optional[spotipy.Spotify], args: argparse.Namespace) -> int:
    aliases = load_aliases()

    if args.alias_cmd == "add":
        playlist_id = parse_playlist_id(args.target)
        aliases[args.name] = playlist_id
        save_aliases(aliases)
        print(f"added alias '{args.name}' -> {playlist_id}")
        return 0

    if args.alias_cmd == "rm":
        if args.name not in aliases:
            raise SpotmvError(f"no such alias: {args.name}")
        removed = aliases.pop(args.name)
        save_aliases(aliases)
        print(f"removed alias '{args.name}' (was {removed})")
        return 0

    if args.alias_cmd == "ls":
        def render() -> None:
            if not aliases:
                print("no aliases defined")
                return
            rows = [[name, pid] for name, pid in sorted(aliases.items())]
            print(render_table(["ALIAS", "PLAYLIST ID"], rows))

        emit(args, dict(sorted(aliases.items())), render)
        return 0

    if args.alias_cmd == "resolve":
        print(resolve_playlist(args.name))
        return 0

    raise SpotmvError("unknown alias subcommand")
