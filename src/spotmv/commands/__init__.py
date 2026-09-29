"""One module per subcommand.

Every module follows the same small contract, which is what lets cli.py stay a
dispatcher and lets tests run a command against a fake client:

    register(sub) -> ArgumentParser   add the subcommand's parser and return it
    run(sp, args) -> int              do the work; `sp` is the Spotify client
    validate(args)                    optional: reject bad input before login
    NEEDS_CLIENT = False              optional: skip login entirely (default True)

Adding a command is one new module here plus one entry in COMMANDS.
"""

from . import (
    alias,
    backup,
    collect_artist,
    describe,
    info,
    ls,
    move_all,
    move_artist,
    rename,
    sort,
    tracks,
)

# order here == order in `spotmv --help`
COMMANDS = [
    ls,
    alias,
    move_artist,
    move_all,
    collect_artist,
    rename,
    tracks,
    sort,
    info,
    describe,
    backup,
]
