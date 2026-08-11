#!/usr/bin/env python3
"""Deterministic checks for session-gated coupon redemptions."""

import json
from pathlib import Path
import subprocess
import sys


WORKDIR = Path(sys.argv[1]).resolve()
RUNNER = r'''import { pathToFileURL } from "node:url";
const root = process.argv[1];
const load = async (name) => import(pathToFileURL(`${root}/${name}`).href);
const { createCoupon } = await load("coupon.js");
const { redeemCoupon } = await load("redemption-service.js");
const { RedemptionStore } = await load("redemption-store.js");
const { SessionAuth } = await load("session-auth.js");

function setup(code = "SAVE20") {
  return {
    store: new RedemptionStore([createCoupon({ code, discountCents: 2_000 })]),
    sessions: new SessionAuth([
      { id: "expired-original", accountId: "buyer-4", status: "expired" },
      { id: "active-original", accountId: "buyer-4", status: "active" },
      { id: "active-rotated", accountId: "buyer-4", status: "active" },
      { id: "revoked-original", accountId: "buyer-4", status: "revoked" },
      { id: "active-outsider", accountId: "buyer-8", status: "active" },
    ]),
  };
}

function request(overrides = {}) {
  return {
    idempotencyKey: "coupon-attempt-4",
    couponCode: "SAVE20",
    accountId: "buyer-4",
    ...overrides,
  };
}

function fingerprint(store) {
  return JSON.stringify(store.snapshot());
}

function authorizedRepeatIsStable() {
  const { store, sessions } = setup();
  const attempt = request();
  const first = redeemCoupon(store, sessions, attempt, "active-original");
  const second = redeemCoupon(store, sessions, attempt, "active-original");
  const state = store.snapshot();
  return JSON.stringify(first) === JSON.stringify(second)
    && state.redemptions.length === 1
    && state.deduplication.length === 1
    && state.nextSequence === 2;
}

function authorizedRotationReplaysOnce() {
  const { store, sessions } = setup("TWENTY");
  const attempt = request({ idempotencyKey: "rotating-key", couponCode: "TWENTY" });
  const first = redeemCoupon(store, sessions, attempt, "active-original");
  const second = redeemCoupon(store, sessions, attempt, "active-rotated");
  const state = store.snapshot();
  return JSON.stringify(first) === JSON.stringify(second)
    && state.redemptions.length === 1
    && state.coupons[0].redeemedBy === "buyer-4";
}

function expiredAttemptLeavesNoTrace() {
  const { store, sessions } = setup();
  const before = fingerprint(store);
  const result = redeemCoupon(store, sessions, request(), "expired-original");
  return JSON.stringify(result) === JSON.stringify({ status: "denied", reason: "session_expired" })
    && fingerprint(store) === before;
}

function accountMismatchLeavesNoTrace() {
  const { store, sessions } = setup();
  const before = fingerprint(store);
  const result = redeemCoupon(store, sessions, request(), "active-outsider");
  return JSON.stringify(result) === JSON.stringify({ status: "denied", reason: "account_mismatch" })
    && fingerprint(store) === before;
}

function expiredThenRotatedSequenceIsGated() {
  const { store, sessions } = setup();
  const attempt = request({ idempotencyKey: "session-cycle" });
  const before = fingerprint(store);
  const deniedFirst = redeemCoupon(store, sessions, attempt, "expired-original");
  const afterDenied = fingerprint(store);
  const redeemed = redeemCoupon(store, sessions, attempt, "active-rotated");
  const deniedAfterSuccess = redeemCoupon(store, sessions, attempt, "revoked-original");
  const replayedForActive = redeemCoupon(store, sessions, attempt, "active-original");
  const state = store.snapshot();
  return JSON.stringify(deniedFirst) === JSON.stringify({ status: "denied", reason: "session_expired" })
    && afterDenied === before
    && redeemed.status === "redeemed"
    && JSON.stringify(deniedAfterSuccess) === JSON.stringify({ status: "denied", reason: "session_revoked" })
    && JSON.stringify(replayedForActive) === JSON.stringify(redeemed)
    && state.redemptions.length === 1
    && state.deduplication.length === 1;
}

process.stdout.write(JSON.stringify({
  authorizedRepeatIsStable: authorizedRepeatIsStable(),
  authorizedRotationReplaysOnce: authorizedRotationReplaysOnce(),
  expiredAttemptLeavesNoTrace: expiredAttemptLeavesNoTrace(),
  accountMismatchLeavesNoTrace: accountMismatchLeavesNoTrace(),
  expiredThenRotatedSequenceIsGated: expiredThenRotatedSequenceIsGated(),
}));
'''
INVARIANT = (
    "Authorized coupon redemption requests sharing an idempotency key must produce one redemption "
    "record and replay the same success without consuming the coupon again, every request must pass "
    "current session authorization before the redemption store reads or writes deduplication state, "
    "and across repeated identical attempts under expired and rotated sessions an authorization "
    "failure must neither reveal an earlier success nor reserve the coupon nor create a deduplication entry."
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
    ("axis1-a", bool(results.get("authorizedRepeatIsStable"))),
    ("axis1-b", bool(results.get("authorizedRotationReplaysOnce"))),
    ("axis2-a", bool(results.get("expiredAttemptLeavesNoTrace"))),
    ("axis2-b", bool(results.get("accountMismatchLeavesNoTrace"))),
    ("interaction", bool(results.get("expiredThenRotatedSequenceIsGated"))),
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
