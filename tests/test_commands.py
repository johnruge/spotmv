"""Commands run against a fake Spotify: the checks a dry run can't do for itself.

A dry run shows you what *would* happen, but it can't prove it wrote nothing,
and it never reaches the --apply path. These tests cover exactly that, plus the
move planner's arithmetic. Everything else is verified by running the tool.
"""

from __future__ import annotations

import json

import pytest
import requests

from fakes import FakeSpotify, make_item, make_playlist, make_track, spotify_error
from spotmv.backups import backups_dir, make_snapshot
from spotmv.planning import by_artist, plan_move
from spotmv.refs import uri_to_id

GYM, CHILL = make_playlist("gym"), make_playlist("chill")
NAS = make_track("N.Y. State of Mind", ["Nas"])
FEAT = make_track("Feature", ["Jay", "Nas"])
OTHER = make_track("Other", ["Someone"])
LOCAL = make_item(make_track("Local File", ["Nas"], is_local=True))


def items(*tracks):
    return [make_item(t) for t in tracks]


@pytest.fixture
def sp(cli_module, monkeypatch):
    """A fake account wired in as the client main() logs in with."""
    fake = FakeSpotify(
        playlists=[GYM, CHILL],
        items={GYM["id"]: items(NAS, OTHER, NAS), CHILL["id"]: items(FEAT)},
        saved=items(FEAT),
    )
    monkeypatch.setattr(cli_module, "get_client", lambda: fake)
    # a saved backup of gym in a different order, for restore
    backups_dir().mkdir(parents=True)
    (backups_dir() / "gym.json").write_text(
        json.dumps(make_snapshot(GYM["id"], "gym", items(OTHER, NAS)))
    )
    return fake


@pytest.mark.parametrize(
    "argv",
    [
        ["move-artist", "--source", GYM["id"], "--dest", CHILL["id"], "--artist", "Nas"],
        ["move-all", "--source", GYM["id"], "--dest", "liked"],
        ["collect-artist", "--dest", CHILL["id"], "--artist", "Nas"],
        ["sort", GYM["id"], "--by", "title"],
        ["restore", "gym.json"],
        ["dupes", GYM["id"]],
        ["copy", "--source", GYM["id"], "--dest", CHILL["id"]],
    ],
    ids=lambda argv: argv[0],
)
def test_dry_run_writes_nothing(cli_module, sp, capsys, argv):
    """The README's core promise, checked on every command that can write."""
    assert cli_module.main(argv) == 0
    assert "DRY RUN" in capsys.readouterr().out
    assert sp.writes == []


@pytest.mark.parametrize(
    "argv, expected",
    [
        (
            ["move-artist", "--source", GYM["id"], "--dest", CHILL["id"], "--artist", "nas"],
            [
                ("playlist_add_items", CHILL["id"], [NAS["uri"]]),
                ("playlist_remove_all_occurrences_of_items", GYM["id"], [NAS["uri"]]),
            ],
        ),
        (  # Liked Songs takes bare track ids on its own endpoints
            ["move-all", "--source", GYM["id"], "--dest", "liked"],
            [
                ("current_user_saved_tracks_add", [uri_to_id(NAS["uri"]), uri_to_id(OTHER["uri"])]),
                ("playlist_remove_all_occurrences_of_items", GYM["id"], [NAS["uri"], OTHER["uri"]]),
            ],
        ),
        (  # back to exactly the saved order
            ["restore", "gym.json"],
            [("playlist_replace_items", GYM["id"], [OTHER["uri"], NAS["uri"]])],
        ),
        (  # gym is NAS, OTHER, NAS: take NAS out, put one copy back at index 0
            ["dupes", GYM["id"]],
            [
                ("playlist_remove_all_occurrences_of_items", GYM["id"], [NAS["uri"]]),
                ("playlist_add_items", GYM["id"], [NAS["uri"]], 0),
            ],
        ),
        (  # like move-artist, but nothing leaves the source
            ["copy", "--source", GYM["id"], "--dest", CHILL["id"], "--artist", "nas"],
            [("playlist_add_items", CHILL["id"], [NAS["uri"]])],
        ),
    ],
    ids=["move-artist", "move-all-to-liked", "restore", "dupes", "copy"],
)
def test_apply_writes_to_the_right_places(cli_module, sp, argv, expected):
    assert cli_module.main(argv + ["--apply"]) == 0
    assert sp.writes == expected


@pytest.mark.parametrize(
    "failure",
    [spotify_error("rate limited", status=429), requests.exceptions.ConnectionError("dropped")],
    ids=["spotify-error", "network-error"],
)
def test_failed_sort_can_be_undone_with_its_backup(cli_module, sp, capsys, failure):
    """sort writes 100 tracks, then appends; if the append fails the playlist is
    left truncated. The error must name a backup that restores it exactly."""
    original = items(*[make_track(f"t{i:03}") for i in range(150)])
    sp.items[GYM["id"]] = original
    sp.fail_on("playlist_add_items", failure)

    assert cli_module.main(["sort", GYM["id"], "--by", "title", "--descending", "--apply"]) == 1
    backup = capsys.readouterr().err.split("spotmv restore ")[1].split()[0]

    # what Spotify now holds: only the first 100 of the new order
    sp.items[GYM["id"]] = [make_item(make_track(u, uri=u)) for u in sp.writes[0][2]]
    sp.calls.clear()
    assert cli_module.main(["restore", backup, "--apply"]) == 0
    restored = [uri for call in sp.writes for uri in call[-1]]
    assert restored == [item["track"]["uri"] for item in original]


def test_plan_counts_every_copy_but_moves_each_track_once():
    plan = plan_move(items(NAS, OTHER, NAS) + [LOCAL] + items(FEAT), [], by_artist(" NAS "))
    assert plan.occurrences == 3  # both copies of NAS + the feature; the local file is skipped
    assert plan.uris == [NAS["uri"], FEAT["uri"]]  # deduped, first-seen order
    assert plan.predicted_source == 2  # OTHER and the local file stay


def test_plan_skips_tracks_already_in_destination():
    plan = plan_move(items(NAS, FEAT), items(FEAT, OTHER))
    assert plan.to_add == [NAS["uri"]]
    assert plan.already_in_dest == 1
    assert plan.predicted_dest == 3
