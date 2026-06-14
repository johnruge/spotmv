# spotmv

A small local command-line tool for managing Spotify playlists via the
[Spotify Web API](https://developer.spotify.com/documentation/web-api) using
[spotipy](https://spotipy.readthedocs.io/).

It can:

- list every playlist you can access (`ls`)
- move all tracks by a given artist from one playlist to another (`move-artist`)
- gather an artist's tracks from every playlist you own into one playlist (`collect-artist`)
- keep only an artist's tracks in a playlist, dropping everything else (`keep-artist`)
- remove duplicate tracks from a playlist (`dedupe`)
- list a playlist's songs with artists, who added them, and when (`tracks`)
- show details about a playlist: track count, total length, owner, etc. (`info`)
- rename a playlist (`rename`) or edit its description (`describe`)
- store playlist aliases so you don't paste IDs/URLs repeatedly (`alias`)

**All destructive actions are dry-run by default.** Nothing changes on Spotify
unless you pass `--apply`.

## Setup

1. Install dependencies (Python 3.9+):

```bash
pip install -r requirements.txt
```

2. Create a Spotify app at the
   [developer dashboard](https://developer.spotify.com/dashboard) and add a
   redirect URI (e.g. `http://127.0.0.1:8888/callback`).

3. Provide your credentials. Copy `.env.example` to `.env` and fill it in:

```bash
cp .env.example .env
```

Or export them in your shell:

```bash
export SPOTIPY_CLIENT_ID=...
export SPOTIPY_CLIENT_SECRET=...
export SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

4. Make the script runnable and put it on your `PATH` (optional):

```bash
chmod +x spotmv
# from the project directory:
./spotmv ls
# or add an alias to your shell config:
alias spotmv="$(pwd)/spotmv"
```

The first command opens a browser once for OAuth login; the token is cached in
`~/.config/spotmv/`.

## Usage

```bash
spotmv ls

spotmv alias add gym https://open.spotify.com/playlist/xxxxxxxxxxxxxxxxxxxxxx
spotmv alias add kendrick spotify:playlist:xxxxxxxxxxxxxxxxxxxxxx
spotmv alias ls
spotmv alias resolve gym
spotmv alias rm gym

# dry run (default): shows what would happen, changes nothing
spotmv move-artist --source gym --dest kendrick --artist "Kendrick Lamar"
# actually do it
spotmv move-artist --source gym --dest kendrick --artist "Kendrick Lamar" --apply

# gather an artist from ALL playlists you own into one playlist
spotmv collect-artist --dest kendrick --artist "Kendrick Lamar"
spotmv collect-artist --dest kendrick --artist "Kendrick Lamar" --apply

# keep only Kendrick's tracks in a playlist, drop the rest (dry-run by default)
spotmv keep-artist gym --artist "Kendrick Lamar"
spotmv keep-artist gym --artist "Kendrick Lamar" --apply

spotmv dedupe gym
spotmv dedupe gym --apply

# list songs with artists, who added them, and when
spotmv tracks gym
spotmv tracks liked

spotmv rename gym "Gym Bangers 2026"
spotmv describe gym "songs for leg day"
spotmv describe gym ""   # clear the description

spotmv info gym
spotmv info liked
```

Aliases work anywhere a playlist argument is accepted. You can also pass a raw
playlist ID, an `open.spotify.com` URL, or a `spotify:playlist:` URI directly.

### Liked Songs

Your Liked Songs library isn't a real playlist in the Spotify API, so it never
appears in `ls` and has no ID/URL to alias. As a convenience, `move-artist`
accepts the keyword `liked` as a source or destination:

```bash
# move an artist's liked songs into a playlist (and unlike them from your library)
spotmv move-artist --source liked --dest kendrick --artist "Kendrick Lamar" --apply

# or pull an artist out of a playlist into Liked Songs
spotmv move-artist --source gym --dest liked --artist "Kendrick Lamar" --apply
```

`dedupe liked` is not supported, since Liked Songs cannot contain duplicates.

> Note: `liked` support uses the `user-library-read` and `user-library-modify`
> scopes. If you authorized an earlier version, the first run after updating will
> open the browser again to grant the new permissions.

## Config location

- Aliases: `~/.config/spotmv/aliases.json`
- OAuth token cache: `~/.config/spotmv/.auth-cache`

Set `SPOTMV_CONFIG_DIR` to override the location.
