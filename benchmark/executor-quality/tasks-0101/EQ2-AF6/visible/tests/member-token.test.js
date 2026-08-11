import assert from "node:assert/strict";
import test from "node:test";

import { loyaltyFixture } from "../fixtures.js";

test("an expired signed token is not authorized", () => {
  const { tokens } = loyaltyFixture();
  assert.deepEqual(tokens.authorize({ value: "token-old", memberId: "member-41", cycleId: "2026-W32" }), {
    authorized: false,
    reason: "token_expired",
  });
});

test("member scope is checked after signature verification", () => {
  const { tokens } = loyaltyFixture();
  const inspected = tokens.inspect("token-outsider");
  assert.equal(inspected.verified, true);
  assert.deepEqual(tokens.authorizeClaims(inspected.claims, { memberId: "member-41", cycleId: "2026-W32" }), {
    authorized: false,
    reason: "token_member_mismatch",
  });
});
