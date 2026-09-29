"""Working out a move before doing it.

move-artist, move-all and collect-artist all take tracks out of one place and
put them somewhere else. plan_move() does the arithmetic once -- which tracks
match, which are duplicates, which the destination already has -- without
touching Spotify, so a dry run and a real run always agree on the numbers.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Sequence

import spotipy

from .api import is_usable_track, item_track
from .errors import SpotmvError
from .refs import resolve_target
from .targets import add_to_target, get_all_target_items, remove_all_from_target, target_name

Track = Dict[str, Any]


@dataclass
class MovePlan:
    source_total: int     # items in the source, including unusable ones
    dest_total: int       # items in the destination
    occurrences: int      # matching source items, counting duplicates -- all get removed
    uris: List[str]       # unique matching uris, first-seen order
    to_add: List[str]     # the subset of uris the destination doesn't have yet

    @property
    def already_in_dest(self) -> int:
        return len(self.uris) - len(self.to_add)

    @property
    def predicted_source(self) -> int:
        return self.source_total - self.occurrences

    @property
    def predicted_dest(self) -> int:
        return self.dest_total + len(self.to_add)


def plan_move(
    source_items: Sequence[Dict[str, Any]],
    dest_items: Sequence[Dict[str, Any]],
    matches: Callable[[Track], bool] = lambda track: True,
) -> MovePlan:
    """Plan moving every usable source track that `matches` into the destination."""
    dest_uris = {item_track(item)["uri"] for item in dest_items if is_usable_track(item)}

    uris: List[str] = []
    seen: set = set()
    occurrences = 0
    for item in source_items:
        if not is_usable_track(item):
            continue
        track = item_track(item)
        if not matches(track):
            continue
        occurrences += 1
        if track["uri"] not in seen:
            seen.add(track["uri"])
            uris.append(track["uri"])

    return MovePlan(
        source_total=len(source_items),
        dest_total=len(dest_items),
        occurrences=occurrences,
        uris=uris,
        to_add=[uri for uri in uris if uri not in dest_uris],
    )


def print_move_summary(plan: MovePlan, source_name: str, dest_name: str, found_label: str) -> None:
    print(f"Source: {source_name}")
    print(f"  Current count: {plan.source_total}")
    print(f"  {found_label}: {plan.occurrences}")
    print(f"  Would remove from source: {plan.occurrences}")
    print(f"  Predicted source count: {plan.predicted_source}")
    print()
    print(f"Destination: {dest_name}")
    print(f"  Current count: {plan.dest_total}")
    print(f"  Would add to destination: {len(plan.to_add)}")
    print(f"  Already in destination: {plan.already_in_dest}")
    print(f"  Predicted destination count: {plan.predicted_dest}")


def run_move(
    sp: spotipy.Spotify,
    args: argparse.Namespace,
    matches: Callable[[Track], bool],
    found_label: str,
) -> int:
    """The shared body of move-artist and move-all: plan, print, and (with --apply) do it."""
    source = resolve_target(args.source)
    dest = resolve_target(args.dest)
    if source == dest:
        raise SpotmvError("source and destination are the same")

    source_name = target_name(sp, source)
    dest_name = target_name(sp, dest)
    plan = plan_move(get_all_target_items(sp, source), get_all_target_items(sp, dest), matches)

    if not args.apply:
        print("DRY RUN: no changes made\n")
        print_move_summary(plan, source_name, dest_name, found_label)
        return 0

    print_move_summary(plan, source_name, dest_name, found_label)
    print()

    if not plan.uris:
        print("nothing to move.")
        return 0

    if plan.to_add:
        add_to_target(sp, dest, plan.to_add)
    remove_all_from_target(sp, source, plan.uris)

    print("DONE")
    print(f"  Added {len(plan.to_add)} track(s) to {dest_name}.")
    print(f"  Removed {plan.occurrences} track(s) from {source_name}.")
    return 0
