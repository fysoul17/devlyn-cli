"""Coordinate waitlist state with the duplicate-entry log."""

from __future__ import annotations

from duplicate_log import DuplicateEntryLog
from models import PromotionOutcome, PromotionRequest
from reason_policy import choose_rejection
from waitlist import PromotionBoard


def submit_promotion(
    board: PromotionBoard,
    log: DuplicateEntryLog,
    request: PromotionRequest,
) -> PromotionOutcome:
    recorded = log.find(request)
    if recorded is not None:
        return recorded

    rejection = choose_rejection(board.rejections_for(request))
    if rejection is not None:
        outcome = PromotionOutcome(
            request.request_key,
            request.candidate_id,
            "rejected",
            rejection.reason,
        )
        log.append(request, outcome)
        return outcome

    board.promote_next(request.candidate_id)
    outcome = PromotionOutcome(
        request.request_key,
        request.candidate_id,
        "promoted",
    )
    log.append(request, outcome)
    return outcome
