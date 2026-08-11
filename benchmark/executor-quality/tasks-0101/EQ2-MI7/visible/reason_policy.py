"""Choose the operator-facing rejection from board validation results."""

from __future__ import annotations

from collections.abc import Iterable

from models import Rejection


REASON_PRIORITY = {
    "paused": 0,
    "full": 1,
    "not_next": 2,
}


def rank_rejections(rejections: Iterable[Rejection]) -> tuple[Rejection, ...]:
    """Return rejections in the order operators should handle them."""

    return tuple(sorted(rejections, key=lambda item: item.source_index))


def choose_rejection(rejections: Iterable[Rejection]) -> Rejection | None:
    ranked = rank_rejections(rejections)
    return ranked[0] if ranked else None
