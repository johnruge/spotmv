"""Turning what you type into something the Spotify API understands.

A "ref" is whatever the user passes on the command line: an alias, a raw id, an
open.spotify.com URL, a spotify:playlist: URI, or the word "liked". A "target" is
the resolved result -- a playlist id, or the LIKED sentinel.
"""

from __future__ import annotations

import re

from .config import load_aliases
from .errors import SpotmvError

# Liked Songs is not a real playlist in the API, so it gets a sentinel value
# that the target helpers branch on.
LIKED = "liked"
LIKED_KEYS = {"liked", "liked-songs", "liked_songs", "saved"}

PLAYLIST_ID_RE = re.compile(r"^[A-Za-z0-9]{22}$")


def parse_playlist_id(value: str) -> str:
    """Normalize a raw id, open.spotify.com URL, or spotify:playlist: URI to an id."""
    value = value.strip()
    if not value:
        raise SpotmvError("empty playlist reference")

    if value.startswith("spotify:playlist:"):
        candidate = value.split(":", 2)[2]
    elif "open.spotify.com" in value:
        match = re.search(r"playlist/([A-Za-z0-9]+)", value)
        if not match:
            raise SpotmvError(f"could not parse playlist id from url: {value}")
        candidate = match.group(1)
    else:
        candidate = value

    candidate = candidate.split("?", 1)[0]
    if not PLAYLIST_ID_RE.match(candidate):
        raise SpotmvError(f"invalid playlist id: {value}")
    return candidate


def resolve_playlist(ref: str) -> str:
    """Resolve an alias name or any playlist reference into a playlist id."""
    aliases = load_aliases()
    if ref in aliases:
        return aliases[ref]
    try:
        return parse_playlist_id(ref)
    except SpotmvError as exc:
        raise SpotmvError(
            f"'{ref}' is not a known alias and is not a valid playlist id/url/uri"
        ) from exc


def resolve_target(ref: str) -> str:
    """Resolve a reference into a playlist id, or the LIKED sentinel for Liked Songs."""
    if ref.strip().lower() in LIKED_KEYS:
        return LIKED
    return resolve_playlist(ref)


def uri_to_id(uri: str) -> str:
    """spotify:track:<id> -> <id> (passes through a bare id)."""
    return uri.rsplit(":", 1)[-1]
