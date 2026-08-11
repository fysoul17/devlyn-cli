import assert from "node:assert/strict";
import test from "node:test";

import { fixture } from "../fixtures.js";

test("expired sessions are denied", () => {
  const { sessions } = fixture();
  assert.deepEqual(sessions.authorize({ sessionId: "session-old", accountId: "account-7" }), {
    authorized: false,
    reason: "session_expired",
  });
});

test("sessions cannot authorize another account", () => {
  const { sessions } = fixture();
  assert.deepEqual(sessions.authorize({ sessionId: "session-other", accountId: "account-7" }), {
    authorized: false,
    reason: "account_mismatch",
  });
});
