from dataclasses import dataclass


@dataclass
class SnapshotDraft:
    snapshot_id: str
    payload: bytes
    fail_after_write: bool = False


@dataclass
class RotationPlan:
    token: str
    retain: int
    drafts: list[SnapshotDraft]


@dataclass(frozen=True)
class CatalogEntry:
    snapshot_id: str
    slot: int
    parent_id: str | None


@dataclass(frozen=True)
class RotationResult:
    ok: bool
    skipped_batch: bool
    applied: tuple[str, ...]
    skipped: tuple[str, ...]
    error: str | None
