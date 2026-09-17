"""Reading from the Spotify Web API: pagination, filtering, batching.

Every list endpoint is paginated, so the get_all_* helpers follow the ``next``
link until it runs out. Nothing here writes -- see targets.py for that.
"""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, Sequence

import spotipy

from .errors import SpotmvError

# Spotify caps playlist writes at 100 items per request, saved-track writes at 50.
BATCH_SIZE = 100
SAVED_BATCH_SIZE = 50


def chunked(items: Sequence[Any], size: int = BATCH_SIZE) -> Iterator[List[Any]]:
    for start in range(0, len(items), size):
        yield list(items[start : start + size])


def get_all_playlists(sp: spotipy.Spotify) -> List[Dict[str, Any]]:
    playlists: List[Dict[str, Any]] = []
    page = sp.current_user_playlists(limit=50)
    while page:
        playlists.extend(pl for pl in (page.get("items") or []) if pl)
        if page.get("next"):
            page = sp.next(page)
        else:
            break
    return playlists


def get_all_playlist_items(sp: spotipy.Spotify, playlist_id: str) -> List[Dict[str, Any]]:
    """Return every playlist item in order, handling pagination."""
    items: List[Dict[str, Any]] = []
    page = sp.playlist_items(
        playlist_id,
        limit=100,
        additional_types=("track",),
    )
    while page:
        items.extend(page.get("items") or [])
        if page.get("next"):
            page = sp.next(page)
        else:
            break
    return items


def item_track(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the track object from a playlist/saved item.

    Spotify returns it under 'track' for saved tracks and (more recently)
    under 'item' for playlist items.
    """
    return item.get("track") or item.get("item")


def is_usable_track(item: Dict[str, Any]) -> bool:
    """True for a real, playable, non-local studio track (not a podcast episode)."""
    track = item_track(item)
    if not track:
        return False
    if track.get("type") != "track":
        return False
    if item.get("is_local") or track.get("is_local"):
        return False
    if track.get("is_playable") is False:
        return False
    if not track.get("uri"):
        return False
    return True


def track_artist_names(track: Dict[str, Any]) -> List[str]:
    return [a.get("name", "") for a in (track.get("artists") or [])]


def playlist_name(sp: spotipy.Spotify, playlist_id: str) -> str:
    """Return a playlist's name (track counts are derived from fetched items)."""
    try:
        data = sp.playlist(playlist_id, fields="name")
    except spotipy.SpotifyException as exc:
        if getattr(exc, "http_status", None) == 404:
            raise SpotmvError(f"playlist not found: {playlist_id}") from exc
        raise SpotmvError(f"could not load playlist {playlist_id}: {exc}") from exc
    return data.get("name") or "(unnamed)"


def get_all_saved_tracks(sp: spotipy.Spotify) -> List[Dict[str, Any]]:
    """Return every Liked Songs item in order, handling pagination."""
    items: List[Dict[str, Any]] = []
    page = sp.current_user_saved_tracks(limit=50)
    while page:
        items.extend(page.get("items") or [])
        if page.get("next"):
            page = sp.next(page)
        else:
            break
    return items


