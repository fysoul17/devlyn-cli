"""Ordered waitlist state and bounded roster mutation."""

from __future__ import annotations

from collections.abc import Iterable

from models import PromotionRequest, Rejection


class PromotionBoard:
    def __init__(
        self,
        queue: Iterable[str],
        capacity: int,
        *,
        roster: Iterable[str] = (),
        paused: Iterable[str] = (),
    ) -> None:
        if capacity < 0:
            raise ValueError("capacity cannot be negative")
        self._queue = list(queue)
        self._capacity = capacity
        self._roster = list(roster)
        self._paused = set(paused)

    @property
    def queue(self) -> tuple[str, ...]:
        return tuple(self._queue)

    @property
    def roster(self) -> tuple[str, ...]:
        return tuple(self._roster)

    def rejections_for(self, request: PromotionRequest) -> tuple[Rejection, ...]:
        rejections: list[Rejection] = []
        if request.candidate_id in self._paused:
            rejections.append(Rejection(0, "paused"))
        if len(self._roster) >= self._capacity:
            rejections.append(Rejection(1, "full"))
        if not self._queue or self._queue[0] != request.candidate_id:
            rejections.append(Rejection(2, "not_next"))
        return tuple(rejections)

    def promote_next(self, candidate_id: str) -> None:
        if not self._queue or self._queue[0] != candidate_id:
            raise ValueError("candidate is not next")
        if len(self._roster) >= self._capacity:
            raise ValueError("roster is full")
        self._queue.pop(0)
        self._roster.append(candidate_id)
