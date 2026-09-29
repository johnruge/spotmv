"""OAuth: turning credentials from the environment into a Spotify client."""

from __future__ import annotations

import logging
import os

import requests
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
        # A plain session: no automatic retries, so a 429 fails fast instead of
        # sleeping through a Retry-After that can be many hours, and the error
        # arrives as a normal HTTP error carrying Spotify's Retry-After header
        # and reason. (spotipy's own retry session replaces a 429 with a bare
        # "Max Retries" error with the headers dropped -- and reports every 5xx
        # as a 429 too.)
        client = spotipy.Spotify(
            auth_manager=auth, requests_session=requests.Session(), requests_timeout=30
        )
        client.current_user()
        return client
    except spotipy.SpotifyOauthError as exc:
        raise SpotmvError(f"authentication failed: {exc}") from exc
    except spotipy.SpotifyException as exc:
        raise SpotmvError(f"could not authenticate with Spotify: {exc}") from exc
