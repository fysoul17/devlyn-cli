import assert from "node:assert/strict";
import test from "node:test";

import { loyaltyFixture } from "../fixtures.js";

test("an expired signed token is not authorized", () => {
  const { tokens } = loyaltyFixture();
  const member = tokens.authenticateMember({ value: "token-old", memberId: "member-41" });
  assert.equal(member.authorized, true);
  assert.deepEqual(tokens.authorizeAccrual(member.claims, "2026-W32"), {
    authorized: false,
    reason: "token_expired",
  });
});

test("member identity is checked after signature verification", () => {
  const { tokens } = loyaltyFixture();
  const inspected = tokens.inspect("token-outsider");
  assert.equal(inspected.verified, true);
  assert.deepEqual(tokens.authenticateMember({ value: "token-outsider", memberId: "member-41" }), {
    authorized: false,
    reason: "token_member_mismatch",
  });
});
