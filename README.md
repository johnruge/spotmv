# spotmv

A small local command-line tool for managing Spotify playlists via the
[Spotify Web API](https://developer.spotify.com/documentation/web-api) using
[spotipy](https://spotipy.readthedocs.io/).

It can:

- list every playlist you can access (`ls`)
- move all tracks by a given artist from one playlist to another (`move-artist`)
- move every track from one playlist into another (`move-all`)
- copy tracks into another playlist without removing them (`copy`)
- gather an artist's tracks from every playlist you own into one playlist (`collect-artist`)
- list a playlist's songs with artists, who added them, and when (`tracks`)
- reorder a playlist by a track attribute (`sort`)
- find and remove duplicate tracks in a playlist (`dupes`)
- search all your playlists and Liked Songs for a song or artist (`find`)
- compare two playlists (`diff`)
- show details about a playlist: track count, total length, owner, etc. (`info`)
- show a playlist's top artists, release decades and length (`stats`)
- back up a playlist's track order and restore it later (`backup`, `backups`, `restore`)
- rename a playlist (`rename`) or edit its description (`describe`)
- store playlist aliases so you don't paste IDs/URLs repeatedly (`alias`)

**All destructive actions are dry-run by default.** Nothing changes on Spotify
unless you pass `--apply`.

## Setup

1. Install dependencies (Python 3.9+) into a virtualenv in the project folder:

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
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

4. Run it with the virtualenv's Python. `spotmv` starts with
   `#!/usr/bin/env python3`, which only finds the dependencies while the
   virtualenv is active, so an alias that names the venv's Python works from
   anywhere:

```bash
# from the project directory:
./venv/bin/python spotmv ls
# or, from the project folder, add an alias with the full paths filled in
# (use ~/.bashrc instead of ~/.zshrc if you use bash):
echo "alias spotmv='$(pwd)/venv/bin/python $(pwd)/spotmv'" >> ~/.zshrc
```

The first command opens a browser once for OAuth login; the token is cached in
`~/.config/spotmv/`. Credentials are read from a `.env` next to the `spotmv`
script first, then from the current directory, then from
`~/.config/spotmv/.env`; anything already exported in your shell wins.

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

# move ALL tracks from one playlist into another (dry-run by default)
spotmv move-all --source gym --dest kendrick
spotmv move-all --source gym --dest kendrick --apply

# gather an artist from ALL playlists you own into one playlist
spotmv collect-artist --dest kendrick --artist "Kendrick Lamar"
spotmv collect-artist --dest kendrick --artist "Kendrick Lamar" --apply

# list songs with artists, who added them, and when
spotmv tracks gym
spotmv tracks liked

# reorder a playlist (dry-run by default)
# keys: release (release date), added (date added), duration, title, artist
# default direction: release/added = descending; duration/title/artist = ascending
# override with --ascending / --descending
spotmv sort gym --by duration --apply   # shortest songs first
spotmv sort gym --by duration --descending --apply

spotmv rename gym "Gym Bangers 2026"
spotmv describe gym "songs for leg day"
spotmv describe gym ""   # clear the description

spotmv info gym
spotmv info liked

# copy instead of move: the source keeps its tracks (dry-run by default)
spotmv copy --source gym --dest kendrick
spotmv copy --source gym --dest kendrick --artist "Kendrick Lamar" --apply

# find tracks that appear more than once; --apply keeps the first copy of each
spotmv dupes gym
spotmv dupes gym --apply

# which of your playlists (and Liked Songs) contain a song or artist?
spotmv find "kendrick"

# what do two playlists share, and what's only in one of them?
spotmv diff gym kendrick
spotmv diff gym liked

# top artists, release decades, total and average length
spotmv stats gym
```

Aliases work anywhere a playlist argument is accepted. You can also pass a raw
playlist ID, an `open.spotify.com` URL, or a `spotify:playlist:` URI directly.

### Backups

`backup` saves a playlist's track order to a local JSON file; `restore` puts the
playlist back exactly as saved. `sort`, `dupes` and `restore` also save a backup
automatically before they change anything.

```bash
spotmv backup gym          # save gym's current track order
spotmv backups             # list saved backups
spotmv backups gym         # ...only gym's

# dry run: shows what would be added back, removed, or reordered
spotmv restore xxxxxxxxxxxxxxxxxxxxxx-20260929-200853.json
spotmv restore xxxxxxxxxxxxxxxxxxxxxx-20260929-200853.json --apply
```

`restore` takes a file name from `spotmv backups` or a path to a backup file.
`backups` works offline; it only reads local files.

### JSON output

The commands that report data take `--json` for scripting: `ls`, `alias ls`,
`info`, `tracks`, `find`, `diff`, `stats` and `backups`. Durations are in
milliseconds, and `diff --json` has the full lists rather than the 15-track
preview.

```bash
spotmv ls --json
spotmv tracks gym --json | jq -r '.tracks[].title'
```

### Liked Songs

Your Liked Songs library isn't a real playlist in the Spotify API, so it never
appears in `ls` and has no ID/URL to alias. Instead, the keyword `liked` works
as a playlist argument for `move-artist`, `move-all`, `copy`, `tracks`, `info`,
`diff` and `stats`, and `find` always searches it. `collect-artist`'s
destination and the commands that edit a playlist itself (`sort`, `dupes`,
`rename`, `describe`, `backup`) don't accept it.

```bash
# move an artist's liked songs into a playlist (and unlike them from your library)
spotmv move-artist --source liked --dest kendrick --artist "Kendrick Lamar" --apply

# or pull an artist out of a playlist into Liked Songs
spotmv move-artist --source gym --dest liked --artist "Kendrick Lamar" --apply
```

> Note: `liked` support uses the `user-library-read` and `user-library-modify`
> scopes. If you authorized an earlier version, the first run after updating will
> open the browser again to grant the new permissions.

## Safety

- **Dry run first.** `move-artist`, `move-all`, `copy`, `collect-artist`,
  `sort`, `dupes` and `restore` only show what they would do until you add
  `--apply`. `rename` and `describe` are the exception: they change the
  playlist immediately.
- **Automatic backups.** `sort`, `dupes` and `restore` rewrite a playlist in
  several API calls (Spotify accepts at most 100 tracks per call), so before
  writing they save the playlist's current track order to the backups folder.
  If a call fails partway (a network error, a rate limit, or Ctrl-C), spotmv
  prints the exact `spotmv restore <file> --apply` line that puts it back.
  Backups are never deleted automatically; clear out old ones by hand.
- **Dates added.** `dupes` removes each duplicated track and re-adds one copy in
  its original position, so the copies it keeps show today as their date added.
  `sort` and `restore` keep the date of every track already in the playlist
  (Spotify preserves it when the track list is replaced); only tracks that
  `restore` adds back show today's date.
- **Local files.** `sort` and `restore` refuse playlists containing local files,
  because local files can't be re-added through the API and replacing the track
  list would delete them. `dupes` leaves local files alone.
- **Liked Songs moves unlike.** Moving tracks out of `liked` removes them from
  your library; use `copy` to keep them.

## Spotify's limits

- **Only playlists you own.** Since Spotify's February 2026 API change, apps can
  only read the tracks of playlists you own. Playlists you follow still appear
  in `ls`, but commands that read their tracks fail with a 403 and an
  explanation.
- **Request quota.** Apps in Spotify's development mode get a limited number of
  requests. `find` and `collect-artist` read every playlist you own, so they use
  the most; avoid running them back to back. If you hit the quota, spotmv shows
  the wait Spotify reports, which can be many hours. Quotas count per developer
  account, so creating another app doesn't reset it.
- **No credits.** Producer and songwriter credits aren't available through the
  Spotify API.

## Config location

- Aliases: `~/.config/spotmv/aliases.json`
- Backups: `~/.config/spotmv/backups/<playlist id>-<UTC timestamp>.json`
- OAuth token cache: `~/.config/spotmv/.auth-cache`

Set `SPOTMV_CONFIG_DIR` to override the location.

## Project structure

```
spotmv                 launcher: puts src/ on the path and runs the CLI
src/spotmv/
  cli.py               builds the parser from commands/, logs in when needed,
                       and turns failures into readable errors
  auth.py              OAuth: credentials from the environment -> Spotify client
  config.py            the config folder, .env lookup, and the alias store
  refs.py              turns aliases, ids, URLs, URIs and "liked" into targets
  api.py               reading from the API: pagination, filtering, batching
  targets.py           playlists and Liked Songs behind one interface
  planning.py          works out a move or copy before doing it
  backups.py           playlist snapshots, and the restore hint on failed writes
  output.py            tables, durations and --json
  errors.py            SpotmvError, for expected user-facing failures
  commands/            one module per subcommand:
    __init__.py          the command contract, and COMMANDS (the --help order)
    alias.py  backup.py  backups.py  collect_artist.py  copy.py  describe.py
    diff.py  dupes.py  find.py  info.py  ls.py  move_all.py  move_artist.py
    rename.py  restore.py  sort.py  stats.py  tracks.py
tests/
  conftest.py          keeps every test offline and away from your real config
  fakes.py             FakeSpotify: an in-memory client that records each call
  test_cli.py          pins the command-line surface
  test_commands.py     dry runs write nothing; --apply sends the right calls
requirements.txt       runtime dependencies
requirements-dev.txt   adds pytest
```

## Development

```bash
./venv/bin/pip install -r requirements-dev.txt
./venv/bin/python -m pytest -q
```

The tests never talk to Spotify: any attempt to log in fails the test, and the
config folder is redirected to a temporary one. The suite is deliberately
small. It pins the command-line surface, checks that every dry run makes no
write calls and that `--apply` sends exactly the expected ones, and covers the
move planner's arithmetic. Everything else is verified by running the real
commands as dry runs against your own playlists.

To add a command, create `src/spotmv/commands/<name>.py` with:

- `register(sub)`: add the subcommand's parser and return it
- `run(sp, args) -> int`: do the work; `sp` is the logged-in Spotify client
- optionally `validate(args)`: reject bad input before logging in
- optionally `NEEDS_CLIENT = False`: skip logging in (e.g. local-only commands)

Then add it to `COMMANDS` in `commands/__init__.py` and to the list in
`tests/test_cli.py`. `commands/ls.py` is the smallest example. A command that
changes Spotify should be a dry run unless `--apply` is given, and should get a
case in `test_dry_run_writes_nothing` and `test_apply_writes_to_the_right_places`.
