"""A target is a playlist id or the LIKED sentinel.

Liked Songs isn't a playlist in the Web API -- it has its own endpoints, takes
bare track ids instead of URIs, and batches at 50 instead of 100. These helpers
hide that difference so commands can treat both the same way.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

import spotipy

from .api import (
    BATCH_SIZE,
    SAVED_BATCH_SIZE,
    chunked,
    get_all_playlist_items,
    get_all_saved_tracks,
    playlist_name,
)
from .refs import LIKED, uri_to_id


def target_name(sp: spotipy.Spotify, target: str) -> str:
    if target == LIKED:
        return "Liked Songs"
    return playlist_name(sp, target)


def get_all_target_items(sp: spotipy.Spotify, target: str) -> List[Dict[str, Any]]:
    if target == LIKED:
        return get_all_saved_tracks(sp)
    return get_all_playlist_items(sp, target)


def add_to_target(sp: spotipy.Spotify, target: str, uris: Sequence[str]) -> None:
    if target == LIKED:
        ids = [uri_to_id(u) for u in uris]
        for batch in chunked(ids, SAVED_BATCH_SIZE):
            sp.current_user_saved_tracks_add(batch)
    else:
        for batch in chunked(list(uris), BATCH_SIZE):
            sp.playlist_add_items(target, batch)


def remove_all_from_target(sp: spotipy.Spotify, target: str, uris: Sequence[str]) -> None:
    if target == LIKED:
        ids = [uri_to_id(u) for u in uris]
        for batch in chunked(ids, SAVED_BATCH_SIZE):
            sp.current_user_saved_tracks_delete(batch)
    else:
        for batch in chunked(list(uris), BATCH_SIZE):
            sp.playlist_remove_all_occurrences_of_items(target, batch)


def replace_playlist_items(sp: spotipy.Spotify, playlist_id: str, uris: Sequence[str]) -> None:
    """Make a playlist contain exactly `uris`, in order.

    Spotify replaces at most 100 items per call, so the rest are appended.
    NOT atomic: if an append fails, the playlist is left holding only the
    first part -- callers should snapshot first (see backups.py).
    """
    uris = list(uris)
    sp.playlist_replace_items(playlist_id, uris[:BATCH_SIZE])
    for batch in chunked(uris[BATCH_SIZE:], BATCH_SIZE):
        sp.playlist_add_items(playlist_id, batch)
