#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import sys
import tempfile


sys.dont_write_bytecode = True
workdir = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(workdir))

from errors import RefundBatchError, StoreFault
from models import Rejection, ReturnRequest
from refund_engine import process_returns
from return_store import ReturnStore


def new_store(
    root: str,
    amounts: dict[str, int],
    *,
    closed: tuple[str, ...] = (),
) -> ReturnStore:
    return ReturnStore.create(pathlib.Path(root) / "orders.json", amounts, closed=closed)


def write_fault_restores_bytes() -> bool:
    with tempfile.TemporaryDirectory() as root:
        store = new_store(root, {"a": 900})
        before = store.snapshot_bytes()
        try:
            process_returns(store, "b1", [ReturnRequest("a", 300, fail_after_write=True)])
        except StoreFault:
            return store.snapshot_bytes() == before
        return False


def finalization_fault_restores_multiple_writes() -> bool:
    with tempfile.TemporaryDirectory() as root:
        store = new_store(root, {"a": 900, "b": 700})
        before = store.snapshot_bytes()
        try:
            process_returns(
                store,
                "b2",
                [ReturnRequest("a", 200), ReturnRequest("b", 150)],
                fail_on_commit=True,
            )
        except StoreFault:
            return store.snapshot_bytes() == before
        return False


def distinct_causes_use_business_precedence() -> bool:
    with tempfile.TemporaryDirectory() as root:
        store = new_store(root, {"a": 800, "b": 500}, closed=("b",))
        try:
            process_returns(
                store,
                "b3",
                [
                    ReturnRequest("b", 50),
                    ReturnRequest("a", 0),
                    ReturnRequest("x", 25),
                ],
            )
        except RefundBatchError as error:
            return error.reason == "bad_amount" and error.rejections == (
                Rejection(1, "bad_amount"),
                Rejection(2, "missing"),
                Rejection(0, "closed"),
            )
        return False


def equal_causes_keep_source_order() -> bool:
    with tempfile.TemporaryDirectory() as root:
        store = new_store(root, {"a": 800, "b": 500}, closed=("b",))
        try:
            process_returns(
                store,
                "b4",
                [
                    ReturnRequest("x", 25),
                    ReturnRequest("b", 50),
                    ReturnRequest("y", 30),
                ],
            )
        except RefundBatchError as error:
            return error.rejections == (
                Rejection(0, "missing"),
                Rejection(2, "missing"),
                Rejection(1, "closed"),
            )
        return False


def ranked_rejection_rolls_back_prior_refund() -> bool:
    with tempfile.TemporaryDirectory() as root:
        store = new_store(root, {"a": 800, "b": 500}, closed=("b",))
        before = store.snapshot_bytes()
        try:
            process_returns(
                store,
                "b5",
                [
                    ReturnRequest("a", 200),
                    ReturnRequest("b", 50),
                    ReturnRequest("a", 0),
                ],
            )
        except RefundBatchError as error:
            ranked = error.reason == "bad_amount" and error.rejections == (
                Rejection(2, "bad_amount"),
                Rejection(1, "closed"),
            )
            return ranked and store.snapshot_bytes() == before
        return False


invariant = "A rejected return batch leaves the order store byte-identical to its pre-batch form, rejection causes are reported by precedence with bad amount before missing order before closed return and arrival order breaking ties, and when successful refund writes precede validation and conflict failures the highest-precedence cause is reported while every earlier write is rolled back."
checks = [
    write_fault_restores_bytes(),
    finalization_fault_restores_multiple_writes(),
    distinct_causes_use_business_precedence(),
    equal_causes_keep_source_order(),
    ranked_rejection_rolls_back_prior_refund(),
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
