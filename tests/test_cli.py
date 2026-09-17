"""The CLI surface, pinned.

Deliberately small: this exists so the restructure (which only moves code
between modules) can't silently drop a command, flag or default. Behaviour is
verified by dry runs against real playlists, not by more tests.
"""

from __future__ import annotations

import pytest

from conftest import find_subparsers

COMMANDS = [
    "ls", "alias", "move-artist", "move-all", "collect-artist",
    "rename", "tracks", "sort", "info", "describe",
]

# every command that can change something on Spotify
DESTRUCTIVE = [
    ["move-artist", "--source", "a", "--dest", "b", "--artist", "c"],
    ["move-all", "--source", "a", "--dest", "b"],
    ["collect-artist", "--dest", "b", "--artist", "c"],
    ["sort", "gym", "--by", "title"],
]


@pytest.fixture
def parser(cli_module):
    return cli_module.build_parser()


def test_subcommands(parser):
    assert list(find_subparsers(parser)) == COMMANDS
    assert set(find_subparsers(find_subparsers(parser)["alias"])) == {
        "add", "rm", "ls", "resolve",
    }
    assert list(
        next(a for a in find_subparsers(parser)["sort"]._actions if a.dest == "by").choices
    ) == ["release", "added", "duration", "title", "artist"]


@pytest.mark.parametrize("argv", DESTRUCTIVE)
def test_apply_is_opt_in(parser, argv):
    """The README's core promise: nothing happens without --apply."""
    assert parser.parse_args(argv).apply is False
    assert parser.parse_args(argv + ["--apply"]).apply is True


@pytest.mark.parametrize(
    "argv",
    [
        [],                                              # a command is required
        ["alias"],                                       # ...and an alias subcommand
        ["move-artist", "--source", "a", "--dest", "b"],  # missing --artist
        ["move-all", "--source", "a"],                   # missing --dest
        ["collect-artist", "--artist", "c"],             # missing --dest
        ["sort", "gym"],                                 # missing --by
        ["sort", "gym", "--by", "bpm"],                  # not a valid sort key
        ["sort", "g", "--by", "title", "--ascending", "--descending"],
        ["rename", "gym"],                               # missing new name
    ],
)
def test_invalid_invocations_are_rejected(parser, argv):
    with pytest.raises(SystemExit):
        parser.parse_args(argv)
