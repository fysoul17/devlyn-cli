#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import sys


sys.dont_write_bytecode = True
workdir = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(workdir))

from duplicate_log import DuplicateEntryLog
from fixtures import full_board, open_board
from models import PromotionRequest, Rejection
from promoter import submit_promotion
from reason_policy import rank_rejections


def successful_retry_moves_once() -> bool:
    board = open_board()
    log = DuplicateEntryLog()
    request = PromotionRequest("a1", "ava")
    first = submit_promotion(board, log, request)
    second = submit_promotion(board, log, request)
    return (
        first == second
        and first.status == "promoted"
        and board.queue == ("ben", "cy")
        and board.roster == ("ava",)
        and len(log.outcomes()) == 1
    )


def rejected_retry_logs_once() -> bool:
    board = full_board()
    log = DuplicateEntryLog()
    request = PromotionRequest("a2", "ava")
    first = submit_promotion(board, log, request)
    second = submit_promotion(board, log, request)
    return (
        first == second
        and first.reason == "full"
        and board.queue == ("ava", "ben", "cy")
        and board.roster == ("zoe",)
        and len(log.outcomes()) == 1
    )


def distinct_reasons_use_business_priority() -> bool:
    ranked = rank_rejections(
        (
            Rejection(0, "not_next"),
            Rejection(1, "paused"),
            Rejection(2, "full"),
        )
    )
    return tuple((item.source_index, item.reason) for item in ranked) == (
        (1, "paused"),
        (2, "full"),
        (0, "not_next"),
    )


def equal_reasons_keep_source_order() -> bool:
    ranked = rank_rejections(
        (
            Rejection(4, "full"),
            Rejection(1, "not_next"),
            Rejection(2, "full"),
        )
    )
    return tuple((item.source_index, item.reason) for item in ranked) == (
        (2, "full"),
        (4, "full"),
        (1, "not_next"),
    )


def changed_duplicate_preserves_first_ranked_error() -> bool:
    board = full_board(paused=("cy",))
    log = DuplicateEntryLog()
    before = (board.queue, board.roster)
    first = submit_promotion(board, log, PromotionRequest("mix", "ava"))
    second = submit_promotion(board, log, PromotionRequest("mix", "cy"))
    return (
        first.reason == "full"
        and second == first
        and (board.queue, board.roster) == before
        and len(log.outcomes()) == 1
    )


invariant = "Within one bounded promotion board, submissions sharing a request key must reuse the first duplicate-log outcome and change the queue or roster at most once, rejection reasons rank paused candidate before full roster before out-of-turn position with source order breaking equal-reason ties, and when duplicate bodies would fail for different reasons the first recorded ranked rejection must remain stable without a second log row or promotion side effect."
checks = [
    successful_retry_moves_once(),
    rejected_retry_logs_once(),
    distinct_reasons_use_business_priority(),
    equal_reasons_keep_source_order(),
    changed_duplicate_preserves_first_ranked_error(),
]
identifiers = ["axis1-a", "axis1-b", "axis2-a", "axis2-b", "interaction"]
print(
    json.dumps(
        {
            "manifestations": [
                {"id": identifier, "invariant": invariant, "passed": passed}
                for identifier, passed in zip(identifiers, checks, strict=True)
            ]
        }
    )
)
