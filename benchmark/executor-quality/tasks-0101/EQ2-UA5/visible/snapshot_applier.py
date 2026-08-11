from errors import SnapshotWriteError


def apply_snapshot(store, draft):
    """Reserve a physical slot and materialize one snapshot draft."""
    slot = store.reserve()
    store.write(slot, draft.snapshot_id, draft.payload)
    if draft.fail_after_write:
        raise SnapshotWriteError(f"write failed: {draft.snapshot_id}")
    return slot
