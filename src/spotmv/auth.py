"""OAuth: turning credentials from the environment into a Spotify client."""

from __future__ import annotations

import logging
import os

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from . import config
from .config import load_env_file
from .errors import SpotmvError

SCOPES = (
    "playlist-read-private "
    "playlist-read-collaborative "
    "playlist-modify-public "
    "playlist-modify-private "
    "user-library-read "
    "user-library-modify"
)


def get_client() -> spotipy.Spotify:
    """Build an authenticated Spotify client from environment variables."""
    logging.getLogger("spotipy").setLevel(logging.CRITICAL)
    load_env_file()

    missing = [
        name
        for name in ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI")
        if not os.environ.get(name)
    ]
    if missing:
        raise SpotmvError(
            "missing environment variables: "
            + ", ".join(missing)
            + "\nset them in your shell or in a local .env file (see .env.example)."
        )

    config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        auth = SpotifyOAuth(
            scope=SCOPES,
            cache_path=str(config.CACHE_PATH),
            open_browser=True,
        )
        # retries=0 so we fail fast on HTTP 429 instead of letting spotipy sleep
        # for the (sometimes enormous) Retry-After interval.
        client = spotipy.Spotify(auth_manager=auth, requests_timeout=30, retries=0)
        client.current_user()
        return client
    except spotipy.SpotifyOauthError as exc:
        raise SpotmvError(f"authentication failed: {exc}") from exc
    except spotipy.SpotifyException as exc:
        raise SpotmvError(f"could not authenticate with Spotify: {exc}") from exc
