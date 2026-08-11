"""Append-only outcomes for promotion submissions."""

from __future__ import annotations

from models import PromotionOutcome, PromotionRequest


class DuplicateEntryLog:
    def __init__(self) -> None:
        self._entries: list[tuple[str, PromotionOutcome]] = []

    @staticmethod
    def _key(request: PromotionRequest) -> str:
        return f"{request.request_key}:{request.candidate_id}"

    def find(self, request: PromotionRequest) -> PromotionOutcome | None:
        key = self._key(request)
        for stored_key, outcome in self._entries:
            if stored_key == key:
                return outcome
        return None

    def append(
        self,
        request: PromotionRequest,
        outcome: PromotionOutcome,
    ) -> None:
        self._entries.append((self._key(request), outcome))

    def outcomes(self) -> tuple[PromotionOutcome, ...]:
        return tuple(outcome for _, outcome in self._entries)
