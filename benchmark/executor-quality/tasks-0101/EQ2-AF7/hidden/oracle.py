#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import sys


sys.dont_write_bytecode = True
workdir = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(workdir))

from conflict_policy import rank_conflicts
from conflict_reporter import ConflictReporter
from fixtures import attendee_conflict_calendar, attendee_request, room_conflict_calendar, room_request
from models import Booking, Conflict
from scheduler import request_slot


def room_retry_publishes_once() -> bool:
    calendar = room_conflict_calendar()
    reporter = ConflictReporter()
    request = room_request("i-one")
    before = calendar.bookings
    first = request_slot(calendar, reporter, request)
    second = request_slot(calendar, reporter, request)
    return (
        first == second
        and first.reason == "room"
        and len(reporter.reports(request.request_id)) == 1
        and reporter.notification_count == 1
        and calendar.bookings == before
    )


def attendee_retry_publishes_once() -> bool:
    calendar = attendee_conflict_calendar()
    reporter = ConflictReporter()
    request = attendee_request("i-two")
    first = request_slot(calendar, reporter, request)
    second = request_slot(calendar, reporter, request)
    return (
        first == second
        and first.reason == "attendee"
        and len(reporter.reports(request.request_id)) == 1
        and reporter.notification_count == 1
        and len(calendar.bookings) == 1
    )


def distinct_reasons_use_operator_priority() -> bool:
    ranked = rank_conflicts(
        (
            Conflict(0, "room", "b1"),
            Conflict(1, "outside", "hours"),
            Conflict(2, "attendee", "b2"),
        )
    )
    return tuple((item.source_index, item.reason) for item in ranked) == (
        (1, "outside"),
        (2, "attendee"),
        (0, "room"),
    )


def equal_reasons_keep_source_order() -> bool:
    ranked = rank_conflicts(
        (
            Conflict(5, "attendee", "b5"),
            Conflict(2, "room", "b2"),
            Conflict(1, "attendee", "b1"),
        )
    )
    return tuple((item.source_index, item.reason) for item in ranked) == (
        (1, "attendee"),
        (5, "attendee"),
        (2, "room"),
    )


def calendar_churn_preserves_sealed_report() -> bool:
    calendar = room_conflict_calendar()
    reporter = ConflictReporter()
    request = room_request("mix")
    first = request_slot(calendar, reporter, request)
    calendar.add_booking(Booking("b-person", "birch", ("ava",), 9 * 60, 10 * 60))
    before_retry = calendar.bookings
    second = request_slot(calendar, reporter, request)
    return (
        first == second
        and first.reason == "room"
        and len(reporter.reports(request.request_id)) == 1
        and reporter.notification_count == 1
        and calendar.bookings == before_retry
    )


invariant = "Slot retries sharing a request id must replay the first conflict report without emitting another notification, conflict reasons rank outside before attendee before room with source order breaking equal-reason ties, and when the calendar changes so an identical retry would now lose to a different conflict the original ranked report must remain sealed without another report or booking side effect."
checks = [
    room_retry_publishes_once(),
    attendee_retry_publishes_once(),
    distinct_reasons_use_operator_priority(),
    equal_reasons_keep_source_order(),
    calendar_churn_preserves_sealed_report(),
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
