#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import sys


sys.dont_write_bytecode = True
workdir = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(workdir))

from discrepancy_reporter import DiscrepancyReporter
from errors import StockFault, TransferRejected
from models import Discrepancy, Transfer
from stock_mover import move_batch
from stock_store import StockStore


def rollback_store() -> StockStore:
    return StockStore(
        {"east": {"A": 1}, "north": {"A": 9, "B": 0}, "west": {"B": 6}},
        {"east": {"A": 8}, "north": {"B": 8}},
    )


def transport_fault_restores_completed_move() -> bool:
    store = rollback_store()
    before = store.snapshot_bytes()
    try:
        move_batch(
            store,
            "f1",
            [
                Transfer("north", "east", "A", 3),
                Transfer("west", "north", "B", 2, fail_before_debit=True),
            ],
        )
    except StockFault:
        return store.snapshot_bytes() == before
    return False


def commit_fault_restores_both_endpoint_pairs() -> bool:
    store = rollback_store()
    before = store.snapshot_bytes()
    try:
        move_batch(
            store,
            "f2",
            [
                Transfer("north", "east", "A", 3),
                Transfer("west", "north", "B", 2),
            ],
            fail_on_commit=True,
        )
    except StockFault:
        return store.snapshot_bytes() == before
    return False


def distinct_reasons_use_business_priority() -> bool:
    reporter = DiscrepancyReporter()
    ranked = reporter.rank(
        [
            Discrepancy(0, "full", "north", "east", "A"),
            Discrepancy(1, "bad_qty", "south", "north", "C"),
            Discrepancy(2, "blocked", "west", "cold", "B"),
        ]
    )
    return tuple((item.source_index, item.reason) for item in ranked) == (
        (1, "bad_qty"),
        (2, "blocked"),
        (0, "full"),
    )


def equal_reasons_keep_source_order() -> bool:
    reporter = DiscrepancyReporter()
    ranked = reporter.rank(
        [
            Discrepancy(4, "blocked", "north", "cold", "A"),
            Discrepancy(3, "bad_qty", "south", "north", "C"),
            Discrepancy(1, "blocked", "west", "cold", "B"),
        ]
    )
    return tuple((item.source_index, item.reason) for item in ranked) == (
        (3, "bad_qty"),
        (1, "blocked"),
        (4, "blocked"),
    )


def ranked_rejection_restores_every_location() -> bool:
    store = StockStore(
        {
            "cold": {"B": 0},
            "east": {"A": 1},
            "north": {"A": 9, "C": 0},
            "south": {"C": 3},
            "west": {"B": 5},
        },
        {"east": {"A": 8}, "north": {"C": 8}},
        blocked=("cold",),
    )
    before = store.snapshot_bytes()
    try:
        move_batch(
            store,
            "f3",
            [
                Transfer("north", "east", "A", 2),
                Transfer("west", "cold", "B", 2),
                Transfer("south", "north", "C", 0),
            ],
        )
    except TransferRejected as error:
        ranked = tuple(
            (item.source_index, item.reason) for item in error.report.ranked
        )
        return (
            error.reason == "bad_qty"
            and ranked == ((2, "bad_qty"), (1, "blocked"))
            and error.report.drift == ()
            and store.snapshot_bytes() == before
        )
    return False


invariant = "Rejected transfer batches restore the serialized multi-location stock ledger byte-for-byte to its pre-batch form, the discrepancy reporter ranks invalid quantity before destination lock before destination capacity with source order breaking equal-reason ties, and when an earlier move plus a later unpaired source debit precede validation and conflict failures the highest-priority discrepancy is returned with zero per-location drift across every touched endpoint."
checks = [
    transport_fault_restores_completed_move(),
    commit_fault_restores_both_endpoint_pairs(),
    distinct_reasons_use_business_priority(),
    equal_reasons_keep_source_order(),
    ranked_rejection_restores_every_location(),
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
