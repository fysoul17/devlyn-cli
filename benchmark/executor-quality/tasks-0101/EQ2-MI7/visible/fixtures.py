"""Small board constructors shared by examples and tests."""

from __future__ import annotations

from waitlist import PromotionBoard


def open_board() -> PromotionBoard:
    return PromotionBoard(("ava", "ben", "cy"), 2)


def full_board(*, paused: tuple[str, ...] = ()) -> PromotionBoard:
    return PromotionBoard(
        ("ava", "ben", "cy"),
        1,
        roster=("zoe",),
        paused=paused,
    )
