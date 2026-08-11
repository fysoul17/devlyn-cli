"""Value objects shared by the meeting scheduler."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SlotRequest:
    request_id: str
    room: str
    attendees: tuple[str, ...]
    start: int
    end: int


@dataclass(frozen=True)
class Booking:
    booking_id: str
    room: str
    attendees: tuple[str, ...]
    start: int
    end: int


@dataclass(frozen=True)
class Conflict:
    source_index: int
    reason: str
    subject: str


@dataclass(frozen=True)
class ConflictReport:
    request_id: str
    reason: str
    source_index: int
    calendar_revision: int


@dataclass(frozen=True)
class ScheduledSlot:
    request_id: str
    booking_id: str
    calendar_revision: int
