"""Room request and confirmed booking records."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RoomRequest:
    request_id: str
    requester: str
    room: str
    start_minute: int
    end_minute: int
    priority: int
    submitted_at: int


@dataclass(frozen=True)
class Booking:
    request_id: str
    room: str
    start_minute: int
    end_minute: int


def normalize_request(raw, submitted_at):
    start = int(raw["start"])
    end = int(raw["end"])
    if start < 0 or end <= start:
        raise ValueError("booking interval must have positive duration")
    return RoomRequest(
        request_id=str(raw["id"]),
        requester=str(raw["requester"]),
        room=str(raw["room"]),
        start_minute=start,
        end_minute=end,
        priority=int(raw["priority"]),
        submitted_at=submitted_at,
    )
