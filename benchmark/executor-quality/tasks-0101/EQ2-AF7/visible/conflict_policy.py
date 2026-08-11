"""Rank meeting conflicts for the operator-facing report."""

from __future__ import annotations

from collections.abc import Iterable

from models import Conflict


REASON_PRIORITY = {
    "outside": 0,
    "attendee": 1,
    "room": 2,
}


def rank_conflicts(conflicts: Iterable[Conflict]) -> tuple[Conflict, ...]:
    """Return conflicts in the order they were discovered."""

    return tuple(sorted(conflicts, key=lambda item: item.source_index))


def choose_conflict(conflicts: Iterable[Conflict]) -> Conflict | None:
    ranked = rank_conflicts(conflicts)
    return ranked[0] if ranked else None
