from models import RotationResult
from snapshot_applier import apply_snapshot


def apply_rotation(store, catalog, plan):
    """Apply a retention plan to physical slots and the catalog."""
    applied = []
    skipped = []
    try:
        for draft in plan.drafts:
            victim = catalog.oldest() if len(catalog) >= plan.retain else None
            slot = apply_snapshot(store, draft)
            if victim is not None:
                catalog.remove(victim.snapshot_id)
            catalog.append(draft.snapshot_id, slot)
            applied.append(draft.snapshot_id)
        catalog.complete(plan.token)
        return RotationResult(True, False, tuple(applied), tuple(skipped), None)
    except Exception as error:
        return RotationResult(
            False, False, tuple(applied), tuple(skipped), str(error)
        )
