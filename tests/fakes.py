"""An in-memory stand-in for the spotipy client.

Implements only the methods spotmv calls. Pages are returned the way the Web API
returns them (a ``next`` token you must follow), and every call is recorded, so a
test can assert exactly what would have been sent to Spotify -- above all, that a
dry run sends nothing.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Sequence

import spotipy

WRITE_METHODS = frozenset({
    "playlist_add_items", "playlist_remove_all_occurrences_of_items",
    "playlist_replace_items", "playlist_change_details",
    "current_user_saved_tracks_add", "current_user_saved_tracks_delete",
})


def fake_id(seed: str) -> str:
    """A deterministic 22-character id, the shape spotmv's regex expects."""
    return hashlib.sha1(seed.encode()).hexdigest()[:22]


def make_track(name: str = "Song", artists: Sequence[str] = ("Artist",), **over: Any) -> Dict[str, Any]:
    track = {
        "name": name,
        "type": "track",
        "uri": f"spotify:track:{fake_id(name)}",
        "artists": [{"name": a} for a in artists],
        "duration_ms": 180_000,
        "album": {"release_date": "2020-01-01"},
        "is_local": False,
    }
    track.update(over)
    return track


def make_item(track: Optional[Dict[str, Any]] = None, *, added_at: str = "2024-01-01T00:00:00Z",
              added_by: str = "me", **track_over: Any) -> Dict[str, Any]:
    return {
        "track": track if track is not None else make_track(**track_over),
        "added_at": added_at,
        "added_by": {"id": added_by},
        "is_local": False,
    }


def make_playlist(name: str, *, owner: str = "me", **over: Any) -> Dict[str, Any]:
    pid = over.pop("playlist_id", fake_id(name))
    playlist = {
        "id": pid,
        "name": name,
        "public": True,
        "collaborative": False,
        "description": "",
        "followers": {"total": 0},
        "owner": {"id": owner, "display_name": owner},
        "external_urls": {"spotify": f"https://open.spotify.com/playlist/{pid}"},
    }
    playlist.update(over)
    return playlist


def spotify_error(message: str = "boom", status: int = 403) -> spotipy.SpotifyException:
    return spotipy.SpotifyException(status, -1, message)


class FakeSpotify:
    """A fake spotipy.Spotify: reads come from memory, writes are recorded."""

    def __init__(self, *, user_id: str = "me", display_name: str = "Me",
                 playlists: Sequence[Dict[str, Any]] = (),
                 items: Optional[Dict[str, List[Dict[str, Any]]]] = None,
                 saved: Sequence[Dict[str, Any]] = (), page_size: int = 100) -> None:
        self.user = {"id": user_id, "display_name": display_name}
        self.playlists = list(playlists)
        self.items = {pid: list(rows) for pid, rows in (items or {}).items()}
        self.saved = list(saved)
        self.page_size = page_size
        self.calls: List[tuple] = []
        self._pages: Dict[str, Dict[str, Any]] = {}

    @property
    def writes(self) -> List[tuple]:
        """Only the calls that would change something. A dry run makes none."""
        return [call for call in self.calls if call[0] in WRITE_METHODS]

    def _record(self, method: str, *args: Any) -> None:
        self.calls.append((method,) + args)

    def _page(self, label: str, rows: Sequence[Dict[str, Any]], size: int) -> Dict[str, Any]:
        size = max(1, size)
        chunks = [list(rows[i:i + size]) for i in range(0, len(rows), size)] or [[]]
        pages = [{"items": c, "next": None, "total": len(rows)} for c in chunks]
        for i in range(len(pages) - 1):
            token = f"fake://{label}/{i + 1}"
            pages[i]["next"] = token
            self._pages[token] = pages[i + 1]
        return pages[0]

    # -- reads ------------------------------------------------------------ #
    def next(self, page: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        token = page.get("next")
        self._record("next", token)
        return self._pages.get(token) if token else None

    def current_user(self) -> Dict[str, Any]:
        self._record("current_user")
        return dict(self.user)

    def current_user_playlists(self, limit: int = 50, **_: Any) -> Dict[str, Any]:
        self._record("current_user_playlists", limit)
        return self._page("playlists", self.playlists, min(self.page_size, limit))

    def playlist_items(self, playlist_id: str, limit: int = 100, **_: Any) -> Dict[str, Any]:
        self._record("playlist_items", playlist_id, limit)
        return self._page(f"items/{playlist_id}", self.items.get(playlist_id, []),
                          min(self.page_size, limit))

    def current_user_saved_tracks(self, limit: int = 50, **_: Any) -> Dict[str, Any]:
        self._record("current_user_saved_tracks", limit)
        return self._page("saved", self.saved, min(self.page_size, limit))

    def playlist(self, playlist_id: str, fields: Optional[str] = None) -> Dict[str, Any]:
        self._record("playlist", playlist_id, fields)
        for pl in self.playlists:
            if pl.get("id") == playlist_id:
                return dict(pl)
        raise spotify_error(f"playlist not found: {playlist_id}", status=404)

    # -- writes (recorded, not simulated) --------------------------------- #
    def playlist_add_items(self, playlist_id: str, uris: Sequence[str]) -> None:
        self._record("playlist_add_items", playlist_id, list(uris))

    def playlist_remove_all_occurrences_of_items(self, playlist_id: str, uris: Sequence[str]) -> None:
        self._record("playlist_remove_all_occurrences_of_items", playlist_id, list(uris))

    def playlist_replace_items(self, playlist_id: str, uris: Sequence[str]) -> None:
        self._record("playlist_replace_items", playlist_id, list(uris))

    def playlist_change_details(self, playlist_id: str, name: Optional[str] = None,
                                description: Optional[str] = None, **_: Any) -> None:
        self._record("playlist_change_details", playlist_id, name, description)

    def current_user_saved_tracks_add(self, tracks: Sequence[str]) -> None:
        self._record("current_user_saved_tracks_add", list(tracks))

    def current_user_saved_tracks_delete(self, tracks: Sequence[str]) -> None:
        self._record("current_user_saved_tracks_delete", list(tracks))
