#!/usr/bin/env python3
import json
import pathlib
import sys


sys.dont_write_bytecode = True
workdir = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(workdir))

from catalog import SnapshotCatalog
from models import CatalogEntry, RotationPlan, SnapshotDraft
from rotation import apply_rotation
from snapshot_store import SnapshotStore


def entry(snapshot_id, slot, parent_id):
    return CatalogEntry(snapshot_id, slot, parent_id)


def draft(snapshot_id, payload, fails=False):
    return SnapshotDraft(snapshot_id, payload, fails)


def durable_state(store, catalog):
    return store.view(), catalog.view()


def failed_write_restores_occupied_slot():
    store = SnapshotStore(2, [(0, "base-a", b"A")], next_slot=0)
    catalog = SnapshotCatalog([entry("base-a", 0, None)], ["prior-token"])
    before = durable_state(store, catalog)
    result = apply_rotation(
        store,
        catalog,
        RotationPlan("failed-one", 1, [draft("candidate-a", b"X", True)]),
    )
    return not result.ok and durable_state(store, catalog) == before


def later_failure_restores_replaced_chain():
    store = SnapshotStore(
        3,
        [(0, "base-b", b"B"), (1, "base-c", b"C"), (2, "base-d", b"D")],
        next_slot=0,
    )
    catalog = SnapshotCatalog(
        [
            entry("base-b", 0, None),
            entry("base-c", 1, "base-b"),
            entry("base-d", 2, "base-c"),
        ],
        ["older-token"],
    )
    before = durable_state(store, catalog)
    result = apply_rotation(
        store,
        catalog,
        RotationPlan(
            "failed-late",
            3,
            [draft("candidate-b", b"Y"), draft("candidate-c", b"Z", True)],
        ),
    )
    return (
        not result.ok
        and result.applied == ("candidate-b",)
        and durable_state(store, catalog) == before
    )


def completed_token_short_circuits_bad_replacement():
    store = SnapshotStore(2, [(0, "kept-a", b"A")], next_slot=1)
    catalog = SnapshotCatalog([entry("kept-a", 0, None)], ["done-token"])
    before = durable_state(store, catalog)
    mark = store.allocation_mark()
    result = apply_rotation(
        store,
        catalog,
        RotationPlan("done-token", 1, [draft("replacement-a", b"X", True)]),
    )
    return (
        result.ok
        and result.skipped_batch
        and durable_state(store, catalog) == before
        and store.allocation_mark() == mark
    )


def repeated_snapshot_identifier_uses_one_slot():
    store = SnapshotStore(4)
    catalog = SnapshotCatalog()
    result = apply_rotation(
        store,
        catalog,
        RotationPlan(
            "dedup-token",
            4,
            [
                draft("fresh-a", b"A"),
                draft("fresh-b", b"B"),
                draft("fresh-a", b"changed"),
            ],
        ),
    )
    return (
        result.ok
        and result.applied == ("fresh-a", "fresh-b")
        and result.skipped == ("fresh-a",)
        and store.allocation_mark() == 2
        and catalog.view()[0]
        == (entry("fresh-a", 0, None), entry("fresh-b", 1, "fresh-a"))
        and catalog.agrees_with(store)
    )


def retry_realigns_ring_with_retention_chain():
    store = SnapshotStore(
        3,
        [(0, "daily-a", b"A"), (1, "daily-b", b"B"), (2, "daily-c", b"C")],
        next_slot=0,
    )
    catalog = SnapshotCatalog(
        [
            entry("daily-a", 0, None),
            entry("daily-b", 1, "daily-a"),
            entry("daily-c", 2, "daily-b"),
        ],
        ["previous-run"],
    )
    plan = RotationPlan(
        "retry-token",
        3,
        [draft("daily-d", b"D"), draft("daily-e", b"E", True)],
    )
    before = durable_state(store, catalog)
    first = apply_rotation(store, catalog, plan)
    rolled_back = durable_state(store, catalog) == before
    plan.drafts[1].fail_after_write = False
    replay = apply_rotation(store, catalog, plan)
    replay_state = durable_state(store, catalog)
    replay_again = apply_rotation(store, catalog, plan)
    return (
        not first.ok
        and rolled_back
        and replay.ok
        and replay.applied == ("daily-d", "daily-e")
        and replay.skipped == ()
        and catalog.view()[0]
        == (
            entry("daily-c", 2, "daily-b"),
            entry("daily-d", 0, "daily-c"),
            entry("daily-e", 1, "daily-d"),
        )
        and store.view()
        == ((0, "daily-d", b"D"), (1, "daily-e", b"E"), (2, "daily-c", b"C"))
        and catalog.agrees_with(store)
        and replay_again.ok
        and replay_again.skipped_batch
        and durable_state(store, catalog) == replay_state
    )


invariant = "A failed rotation restores every physical snapshot slot and catalog entry to its pre-rotation value, completed rotation tokens and snapshot identifiers take effect at most once, and retrying the same plan after that rollback resumes at the clean allocation position so the retention chain and physical slot ownership advance exactly once."
checks = [
    failed_write_restores_occupied_slot(),
    later_failure_restores_replaced_chain(),
    completed_token_short_circuits_bad_replacement(),
    repeated_snapshot_identifier_uses_one_slot(),
    retry_realigns_ring_with_retention_chain(),
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
