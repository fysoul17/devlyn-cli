#!/usr/bin/env python3
import json
import pathlib
import sys


sys.dont_write_bytecode = True
workdir = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(workdir))

from booking import schedule_day


passes = {
    "member": {"shared", "secure"},
    "visitor": {"lobby"},
}
room_zones = {
    "atlas": "shared",
    "board": "secure",
    "lobby": "lobby",
}


def request(identifier, requester, room, start, end, priority):
    return {
        "id": identifier,
        "requester": requester,
        "room": room,
        "start": start,
        "end": end,
        "priority": priority,
    }


def view(result):
    return (
        [item["id"] for item in result["confirmed"]],
        result["denied"],
        result["unavailable"],
    )


first_order = schedule_day(
    [
        request("low", "member", "board", 540, 600, 1),
        request("urgent", "member", "board", 540, 600, 9),
    ],
    passes,
    room_zones,
)
axis1_a = view(first_order) == (["urgent"], [], ["low"])

tied_order = schedule_day(
    [
        request("first", "member", "atlas", 600, 660, 5),
        request("second", "member", "atlas", 600, 660, 5),
    ],
    passes,
    room_zones,
)
axis1_b = view(tied_order) == (["first"], [], ["second"])

denied_only = schedule_day(
    [request("blocked", "visitor", "board", 480, 540, 8)],
    passes,
    room_zones,
)
axis2_a = view(denied_only) == ([], ["blocked"], [])

separate_access = schedule_day(
    [
        request("denied", "visitor", "board", 480, 540, 8),
        request("allowed", "member", "atlas", 600, 660, 2),
    ],
    passes,
    room_zones,
)
axis2_b = view(separate_access) == (["allowed"], ["denied"], [])

composed = schedule_day(
    [
        request("blocked-board", "visitor", "board", 540, 600, 10),
        request("team-atlas", "member", "atlas", 600, 660, 7),
        request("blocked-atlas", "visitor", "atlas", 480, 540, 5),
        request("team-board", "member", "board", 540, 600, 2),
    ],
    passes,
    room_zones,
)
interaction = view(composed) == (
    ["team-atlas", "team-board"],
    ["blocked-board", "blocked-atlas"],
    [],
)

invariant = "Room requests are evaluated by descending booking priority with submission order breaking ties, the access policy admits only requesters whose passes cover the requested room's zone, and when privileged and unprivileged requests interleave authorization is decided before calendar placement so denied requests never consume ordered calendar intervals or displace an authorized meeting."

print(json.dumps({"manifestations": [
    {"id": "axis1-a", "invariant": invariant, "passed": axis1_a},
    {"id": "axis1-b", "invariant": invariant, "passed": axis1_b},
    {"id": "axis2-a", "invariant": invariant, "passed": axis2_a},
    {"id": "axis2-b", "invariant": invariant, "passed": axis2_b},
    {"id": "interaction", "invariant": invariant, "passed": interaction},
]}))
