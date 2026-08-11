"""Stable business precedence for return rejection causes."""

from __future__ import annotations

from collections.abc import Iterable

from models import Rejection


REASON_PRIORITY = {
    "bad_amount": 0,
    "missing": 1,
    "closed": 2,
}


def rank_rejections(rejections: Iterable[Rejection]) -> tuple[Rejection, ...]:
    """Rank causes by business precedence, preserving arrival ties."""

    return tuple(
        sorted(
            rejections,
            key=lambda rejection: (
                REASON_PRIORITY[rejection.reason],
                rejection.source_index,
            ),
        )
    )
