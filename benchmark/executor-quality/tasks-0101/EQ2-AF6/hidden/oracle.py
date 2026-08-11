#!/usr/bin/env python3
"""Deterministic checks for authorized loyalty statement folding."""

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
      { value: "forged-member", tokenId: "forged", memberId: "member-41", status: "active", cycles: ["2026-W32"], signature: "untrusted" },
    ]),
  };
}

function event(eventId, points) {
  return createAccrualEvent({ eventId, cycleId: "2026-W32", points });
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

function sameBatchOccupiesOneStatementLine() {
  const { store, tokens } = setup();
  const batch = request();
  const first = postAccrual(store, tokens, batch, "active-current");
  const second = postAccrual(store, tokens, batch, "active-rotated");
  const [statement] = store.snapshot().statements;
  return JSON.stringify(first) === JSON.stringify(second)
    && first.pointsAwarded === 55
    && statement.batches.length === 1
    && statement.cyclePoints === 55
    && statement.closingBalance === 55;
}

function changedPayloadCannotEscapeStatementKey() {
  const { store, tokens } = setup();
  const firstBatch = request({
    idempotencyKey: "statement-key",
    events: [event("hotel-80", 80), event("bonus-50", 50)],
  });
  const changedRetry = request({
    idempotencyKey: "statement-key",
    events: [event("late-adjustment", 10)],
  });
  const first = postAccrual(store, tokens, firstBatch, "active-current");
  const second = postAccrual(store, tokens, changedRetry, "active-rotated");
  const [statement] = store.snapshot().statements;
  return JSON.stringify(first) === JSON.stringify(second)
    && JSON.stringify(first.allocations) === JSON.stringify([
      { eventId: "hotel-80", points: 80 },
      { eventId: "bonus-50", points: 20 },
    ])
    && statement.batches.length === 1
    && statement.cyclePoints === 100;
}

function forgedSignatureCannotOpenStatement() {
  const { store, tokens } = setup();
  const before = fingerprint(store);
  const result = postAccrual(store, tokens, request(), "forged-member");
  return JSON.stringify(result) === JSON.stringify({ status: "denied", reason: "token_invalid" })
    && fingerprint(store) === before;
}

function differentMemberCannotOpenStatement() {
  const { store, tokens } = setup();
  const before = fingerprint(store);
  const result = postAccrual(store, tokens, request(), "active-outsider");
  return JSON.stringify(result) === JSON.stringify({ status: "denied", reason: "token_member_mismatch" })
    && fingerprint(store) === before;
}

function expiredCapClosingBatchWaitsForRotatedToken() {
  const { store, tokens } = setup(100);
  const seed = request({
    idempotencyKey: "cycle-opening",
    events: [event("seed-purchase", 70)],
  });
  const seeded = postAccrual(store, tokens, seed, "active-current");
  const target = request({
    idempotencyKey: "cap-closing",
    events: [event("partner-stay", 40), event("survey-bonus", 20)],
  });
  const beforeDenied = fingerprint(store);
  const denied = postAccrual(store, tokens, target, "expired-old");
  const afterDenied = fingerprint(store);
  const posted = postAccrual(store, tokens, target, "active-rotated");
  const [statement] = store.snapshot().statements;
  return seeded.pointsAwarded === 70
    && JSON.stringify(denied) === JSON.stringify({ status: "denied", reason: "token_expired" })
    && afterDenied === beforeDenied
    && posted.pointsAwarded === 30
    && JSON.stringify(posted.allocations) === JSON.stringify([{ eventId: "partner-stay", points: 30 }])
    && statement.cyclePoints === 100
    && statement.closingBalance === 100
    && statement.batches.length === 2
    && JSON.stringify(statement.batches.map((batch) => batch.idempotencyKey)) === JSON.stringify([
      "cycle-opening",
      "cap-closing",
    ]);
}

process.stdout.write(JSON.stringify({
  sameBatchOccupiesOneStatementLine: sameBatchOccupiesOneStatementLine(),
  changedPayloadCannotEscapeStatementKey: changedPayloadCannotEscapeStatementKey(),
  forgedSignatureCannotOpenStatement: forgedSignatureCannotOpenStatement(),
  differentMemberCannotOpenStatement: differentMemberCannotOpenStatement(),
  expiredCapClosingBatchWaitsForRotatedToken: expiredCapClosingBatchWaitsForRotatedToken(),
}));
'''
INVARIANT = (
    "Within each member cycle, authorized loyalty accrual batches sharing an idempotency key must "
    "occupy one statement entry and fold their event points into the cycle total and cap exactly once, "
    "complete member-token authorization (signature, member, status, and cycle scope) must finish before "
    "the accrual store folds any batch into that statement, and when an expired token is followed by a "
    "rotated authorized token for the same cap-closing batch the denial must leave the aggregate untouched "
    "so only the authorized retry records the entry and consumes the remaining cap."
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
    ("axis1-a", bool(results.get("sameBatchOccupiesOneStatementLine"))),
    ("axis1-b", bool(results.get("changedPayloadCannotEscapeStatementKey"))),
    ("axis2-a", bool(results.get("forgedSignatureCannotOpenStatement"))),
    ("axis2-b", bool(results.get("differentMemberCannotOpenStatement"))),
    ("interaction", bool(results.get("expiredCapClosingBatchWaitsForRotatedToken"))),
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
