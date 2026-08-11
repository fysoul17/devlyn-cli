#!/usr/bin/env python3
"""Deterministic checks for token-gated periodic loyalty accrual."""

import json
from pathlib import Path
import subprocess
import sys


WORKDIR = Path(sys.argv[1]).resolve()
RUNNER = r'''import { pathToFileURL } from "node:url";
const root = process.argv[1];
const load = async (name) => import(pathToFileURL(`${root}/${name}`).href);
const { createAccrualEvent } = await load("accrual-event.js");
const { postAccrual } = await load("accrual-service.js");
const { AccrualStore } = await load("accrual-store.js");
const { CyclePolicy } = await load("cycle-policy.js");
const { MemberTokenRegistry } = await load("member-token.js");

function setup(maxPoints = 100) {
  return {
    store: new AccrualStore({
      members: [{ memberId: "member-41", balance: 0 }, { memberId: "member-99", balance: 200 }],
      policy: new CyclePolicy(maxPoints),
    }),
    tokens: new MemberTokenRegistry([
      { value: "expired-old", tokenId: "old", memberId: "member-41", status: "expired", cycles: ["2026-W32"], signature: "trusted" },
      { value: "active-current", tokenId: "current", memberId: "member-41", status: "active", cycles: ["2026-W32"], signature: "trusted" },
      { value: "active-rotated", tokenId: "rotated", memberId: "member-41", status: "active", cycles: ["2026-W32"], signature: "trusted" },
      { value: "active-outsider", tokenId: "outsider", memberId: "member-99", status: "active", cycles: ["2026-W32"], signature: "trusted" },
    ]),
  };
}

function event(eventId, points, cycleId = "2026-W32") {
  return createAccrualEvent({ eventId, points, cycleId });
}

function request(overrides = {}) {
  return {
    idempotencyKey: "periodic-41",
    memberId: "member-41",
    cycleId: "2026-W32",
    events: [event("purchase-41", 40), event("review-41", 15)],
    ...overrides,
  };
}

function fingerprint(store) {
  return JSON.stringify(store.snapshot());
}

function repeatedAggregationHasOneReceipt() {
  const { store, tokens } = setup();
  const batch = request();
  const first = postAccrual(store, tokens, batch, "active-current");
  const second = postAccrual(store, tokens, batch, "active-current");
  const state = store.snapshot();
  return JSON.stringify(first) === JSON.stringify(second)
    && first.pointsAwarded === 55
    && state.receipts.length === 1
    && state.receiptsByKey.length === 1
    && state.eventPostings.length === 2
    && state.cycleTotals[0][1] === 55;
}

function cappedAggregationReplaysExactly() {
  const { store, tokens } = setup(100);
  const batch = request({
    idempotencyKey: "cap-boundary",
    events: [event("stay-80", 80), event("bonus-50", 50)],
  });
  const first = postAccrual(store, tokens, batch, "active-current");
  const second = postAccrual(store, tokens, batch, "active-rotated");
  const state = store.snapshot();
  return JSON.stringify(first) === JSON.stringify(second)
    && first.pointsAwarded === 100
    && JSON.stringify(first.allocations) === JSON.stringify([
      { eventId: "stay-80", points: 80 },
      { eventId: "bonus-50", points: 20 },
    ])
    && state.receipts.length === 1
    && state.cycleTotals[0][1] === 100;
}

function expiredTokenCannotTouchStore() {
  const { store, tokens } = setup();
  const before = fingerprint(store);
  const result = postAccrual(store, tokens, request(), "expired-old");
  return JSON.stringify(result) === JSON.stringify({ status: "denied", reason: "token_expired" })
    && fingerprint(store) === before;
}

function memberScopeCannotTouchStore() {
  const { store, tokens } = setup();
  const before = fingerprint(store);
  const result = postAccrual(store, tokens, request(), "active-outsider");
  return JSON.stringify(result) === JSON.stringify({ status: "denied", reason: "token_member_mismatch" })
    && fingerprint(store) === before;
}

function rotatedTokenSequencePreservesCycleState() {
  const { store, tokens } = setup(100);
  const seed = request({
    idempotencyKey: "cycle-seed",
    events: [event("seed-purchase", 30)],
  });
  const seeded = postAccrual(store, tokens, seed, "active-current");
  const target = request({
    idempotencyKey: "rotation-cycle",
    events: [event("hotel-stay", 60), event("partner-bonus", 20)],
  });
  const beforeDenied = fingerprint(store);
  const deniedBefore = postAccrual(store, tokens, target, "expired-old");
  const afterDenied = fingerprint(store);
  const accrued = postAccrual(store, tokens, target, "active-rotated");
  const deniedAfter = postAccrual(store, tokens, target, "expired-old");
  const replayed = postAccrual(store, tokens, target, "active-current");
  const state = store.snapshot();
  return seeded.pointsAwarded === 30
    && JSON.stringify(deniedBefore) === JSON.stringify({ status: "denied", reason: "token_expired" })
    && afterDenied === beforeDenied
    && accrued.pointsAwarded === 70
    && JSON.stringify(accrued.allocations) === JSON.stringify([
      { eventId: "hotel-stay", points: 60 },
      { eventId: "partner-bonus", points: 10 },
    ])
    && JSON.stringify(deniedAfter) === JSON.stringify({ status: "denied", reason: "token_expired" })
    && JSON.stringify(replayed) === JSON.stringify(accrued)
    && state.cycleTotals[0][1] === 100
    && state.balances[0][1] === 100
    && state.receipts.length === 2
    && state.receiptsByKey.length === 2;
}

process.stdout.write(JSON.stringify({
  repeatedAggregationHasOneReceipt: repeatedAggregationHasOneReceipt(),
  cappedAggregationReplaysExactly: cappedAggregationReplaysExactly(),
  expiredTokenCannotTouchStore: expiredTokenCannotTouchStore(),
  memberScopeCannotTouchStore: memberScopeCannotTouchStore(),
  rotatedTokenSequencePreservesCycleState: rotatedTokenSequencePreservesCycleState(),
}));
'''
INVARIANT = (
    "Authorized loyalty accrual batches sharing an idempotency key must replay one cycle receipt "
    "without reapplying event points or consuming the member's cycle cap, complete member-token "
    "authorization (status plus member and cycle scopes) must occur before the accrual store reads or "
    "writes receipt state, and when identical periodic accrual attempts span expired and rotated tokens "
    "only authorized calls may create or reveal the receipt so denied calls leave balances, cap usage, "
    "and idempotency state unchanged."
)


completed = subprocess.run(
    ["node", "--input-type=module", "--eval", RUNNER, str(WORKDIR)],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
    timeout=15,
)
try:
    results = json.loads(completed.stdout) if completed.returncode == 0 else {}
except json.JSONDecodeError:
    results = {}

checks = [
    ("axis1-a", bool(results.get("repeatedAggregationHasOneReceipt"))),
    ("axis1-b", bool(results.get("cappedAggregationReplaysExactly"))),
    ("axis2-a", bool(results.get("expiredTokenCannotTouchStore"))),
    ("axis2-b", bool(results.get("memberScopeCannotTouchStore"))),
    ("interaction", bool(results.get("rotatedTokenSequencePreservesCycleState"))),
]

print(
    json.dumps(
        {
            "manifestations": [
                {"id": identifier, "invariant": INVARIANT, "passed": passed}
                for identifier, passed in checks
            ]
        },
        separators=(",", ":"),
    )
)
