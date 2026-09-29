"""Terminal output helpers. No Spotify dependency -- pure formatting."""

from __future__ import annotations

import argparse
import json
from typing import Any, Callable, Sequence


def render_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Render rows as a left-aligned, space-padded table under a rule."""
    columns = list(zip(*([headers] + [list(r) for r in rows]))) if rows else [[h] for h in headers]
    widths = [max(len(str(cell)) for cell in col) for col in columns]

    def fmt(row: Sequence[str]) -> str:
        return "  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row))

    line = "  ".join("-" * w for w in widths)
    out = [fmt(headers), line]
    out.extend(fmt(row) for row in rows)
    return "\n".join(out)


def format_duration(ms: int) -> str:
    """Format milliseconds as e.g. '3h 24m 11s', dropping empty leading units."""
    seconds = ms // 1000
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json", action="store_true", help="print machine-readable JSON instead of text"
    )


def emit(args: argparse.Namespace, data: Any, render: Callable[[], None]) -> None:
    """Print `data` as JSON if --json was given, otherwise call `render` for the text."""
    if getattr(args, "json", False):
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        render()
