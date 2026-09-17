"""Terminal output helpers. No Spotify dependency -- pure formatting."""

from __future__ import annotations

from typing import Sequence


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
