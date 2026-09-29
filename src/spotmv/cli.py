#!/usr/bin/env python3
"""spotmv - a small local CLI for managing Spotify playlists.

This module is only the dispatcher: it builds the parser from commands/,
logs in when a command needs it, and turns failures into readable errors.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

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
from .auth import get_client  # noqa: E402
from .commands import COMMANDS  # noqa: E402
from .errors import SpotmvError  # noqa: E402
from .output import format_duration  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spotmv",
        description="Manage Spotify playlists from the command line.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for command in COMMANDS:
        command.register(sub).set_defaults(handler=command)
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
    command = args.handler
    try:
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
