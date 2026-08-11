"""Public values used by the waitlist promotion flow."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromotionRequest:
    request_key: str
    candidate_id: str


@dataclass(frozen=True)
class Rejection:
    source_index: int
    reason: str


@dataclass(frozen=True)
class PromotionOutcome:
    request_key: str
    candidate_id: str
    status: str
    reason: str | None = None
