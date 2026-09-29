#!/usr/bin/env python3
"""spotmv - a small local CLI for managing Spotify playlists."""

from __future__ import annotations

import argparse
import sys
from typing import Any, Dict, Optional, Sequence

try:
    import requests
    import spotipy
except ImportError:
    sys.stderr.write(
        "error: the 'spotipy' package is required.\n"
        "       install dependencies with: pip install -r requirements.txt\n"
    )
    sys.exit(1)

# must follow the import check above, hence the noqa: E402s
from .api import (  # noqa: E402
    chunked,
    get_all_playlist_items,
    item_track,
    playlist_name,
    track_artist_names,
)
from .auth import get_client  # noqa: E402
from .commands import alias, collect_artist, describe, info, ls, move_all, move_artist, rename, tracks  # noqa: E402
from .errors import SpotmvError  # noqa: E402
from .output import format_duration  # noqa: E402
from .refs import (  # noqa: E402
    LIKED_KEYS,
    resolve_playlist,
)


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
SORT_KEYS = ("release", "added", "duration", "title", "artist")
DEFAULT_DESCENDING = {"release", "added"}


def _sort_key_func(key: str):
    """Return a function mapping an item to a sortable value for the given key."""

    def getter(item: Dict[str, Any]):
        track = item_track(item) or {}
        if key == "added":
            return item.get("added_at") or ""
        if key == "release":
            return (track.get("album") or {}).get("release_date") or ""
        if key == "title":
            return (track.get("name") or "").lower()
        if key == "artist":
            names = track_artist_names(track)
            return (names[0] if names else "").lower()
        if key == "duration":
            return track.get("duration_ms") or 0
        return ""

    return getter


def cmd_sort(args: argparse.Namespace) -> int:
    if args.playlist.strip().lower() in LIKED_KEYS:
        raise SpotmvError("sort is only supported for playlists, not Liked Songs")

    sp = get_client()
    playlist_id = resolve_playlist(args.playlist)
    name = playlist_name(sp, playlist_id)
    items = get_all_playlist_items(sp, playlist_id)

    if any(item_track(item) is None for item in items):
        raise SpotmvError(
            "this playlist contains unsupported items that cannot be reordered safely"
        )
    if any(
        item.get("is_local") or (item_track(item) or {}).get("is_local")
        for item in items
    ):
        raise SpotmvError(
            "sort does not support playlists containing local files "
            "(they cannot be re-added via the API)"
        )

    if args.ascending:
        descending = False
    elif args.descending:
        descending = True
    else:
        descending = args.by in DEFAULT_DESCENDING

    ordered = sorted(items, key=_sort_key_func(args.by), reverse=descending)

    direction = "descending" if descending else "ascending"

    def label(item: Dict[str, Any]) -> str:
        track = item_track(item)
        artists = ", ".join(track_artist_names(track)) or "-"
        return f"{track.get('name') or '(unknown)'} - {artists}"

    def print_summary() -> None:
        print(f"Playlist: {name} ({len(items)} tracks)")
        print(f"Sorting by {args.by}, {direction}.\n")
        preview = min(len(ordered), 15)
        for i in range(preview):
            print(f"  {i + 1:>3}. {label(ordered[i])}")
        if len(ordered) > preview:
            print(f"  ... and {len(ordered) - preview} more")

    if not args.apply:
        print("DRY RUN: no changes made\n")
        print_summary()
        return 0

    print_summary()
    print()

    new_uris = [item_track(item)["uri"] for item in ordered]
    try:
        sp.playlist_replace_items(playlist_id, new_uris[:100])
        for batch in chunked(new_uris[100:]):
            sp.playlist_add_items(playlist_id, batch)
    except spotipy.SpotifyException as exc:
        if getattr(exc, "http_status", None) == 403:
            raise SpotmvError(
                f"not allowed to modify this playlist (you may not be the owner): {name}"
            ) from exc
        raise SpotmvError(f"could not reorder playlist: {exc}") from exc

    print("DONE")
    print(f"  Reordered {len(new_uris)} track(s) in {name} by {args.by} ({direction}).")
    return 0


# --------------------------------------------------------------------------- #
# CLI wiring
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spotmv",
        description="Manage Spotify playlists from the command line.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ls.register(sub).set_defaults(handler=ls)

    alias.register(sub).set_defaults(handler=alias)

    move_artist.register(sub).set_defaults(handler=move_artist)

    move_all.register(sub).set_defaults(handler=move_all)

    collect_artist.register(sub).set_defaults(handler=collect_artist)

    rename.register(sub).set_defaults(handler=rename)

    tracks.register(sub).set_defaults(handler=tracks)

    srt = sub.add_parser(
        "sort",
        help="reorder a playlist by a track attribute (descending by default)",
    )
    srt.add_argument("playlist", help="playlist or alias")
    srt.add_argument(
        "--by",
        required=True,
        choices=SORT_KEYS,
        help="sort key: release date, date added, duration, title, or artist "
        "(default direction: release/added descending, duration/title/artist ascending)",
    )
    direction = srt.add_mutually_exclusive_group()
    direction.add_argument(
        "--ascending", action="store_true", help="force ascending order"
    )
    direction.add_argument(
        "--descending", action="store_true", help="force descending order"
    )
    srt.add_argument(
        "--apply", action="store_true", help="perform changes (default is dry-run)"
    )
    srt.set_defaults(func=cmd_sort)

    info.register(sub).set_defaults(handler=info)

    describe.register(sub).set_defaults(handler=describe)

    return parser


def _handle_rate_limit(exc: spotipy.SpotifyException) -> None:
    headers = getattr(exc, "headers", None) or {}
    retry_after = headers.get("Retry-After") if hasattr(headers, "get") else None
    sys.stderr.write("error: Spotify is rate-limiting this app (HTTP 429).\n")
    if retry_after:
        try:
            secs = int(retry_after)
            sys.stderr.write(
                f"       Spotify asks to wait ~{format_duration(secs * 1000)} before retrying.\n"
            )
        except ValueError:
            pass
    sys.stderr.write(
        "       Rate limits are per Spotify app and reset after the wait above.\n"
        "       Tip: avoid running large scans repeatedly; if you're blocked for a\n"
        "       long time, you can create a new app in the dashboard for a fresh limit.\n"
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        command = getattr(args, "handler", None)
        if command is None:
            # not yet moved into commands/ -- this branch goes away once all are
            return args.func(args)
        # validate before logging in, so bad input fails fast and offline
        validate = getattr(command, "validate", None)
        if validate is not None:
            validate(args)
        sp = get_client() if getattr(command, "NEEDS_CLIENT", True) else None
        return command.run(sp, args)
    except SpotmvError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1
    except spotipy.SpotifyException as exc:
        if getattr(exc, "http_status", None) == 429:
            _handle_rate_limit(exc)
        else:
            sys.stderr.write(f"spotify api error: {exc}\n")
        return 1
    except requests.exceptions.RequestException as exc:
        sys.stderr.write(f"error: network problem talking to Spotify: {exc}\n")
        return 1
    except KeyboardInterrupt:
        sys.stderr.write("\naborted.\n")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
