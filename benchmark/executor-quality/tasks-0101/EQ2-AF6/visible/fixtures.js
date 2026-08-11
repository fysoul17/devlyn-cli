import { createAccrualEvent } from "./accrual-event.js";
import { AccrualStore } from "./accrual-store.js";
import { CyclePolicy } from "./cycle-policy.js";
import { MemberTokenRegistry } from "./member-token.js";

export function loyaltyFixture({ maxPoints = 100 } = {}) {
  return {
    store: new AccrualStore({
      members: [
        { memberId: "member-41", balance: 0 },
        { memberId: "member-99", balance: 200 },
      ],
      policy: new CyclePolicy(maxPoints),
    }),
    tokens: new MemberTokenRegistry([
      { value: "token-old", tokenId: "old", memberId: "member-41", status: "expired", cycles: ["2026-W32"], signature: "trusted" },
      { value: "token-current", tokenId: "current", memberId: "member-41", status: "active", cycles: ["2026-W32"], signature: "trusted" },
      { value: "token-rotated", tokenId: "rotated", memberId: "member-41", status: "active", cycles: ["2026-W32"], signature: "trusted" },
      { value: "token-outsider", tokenId: "outsider", memberId: "member-99", status: "active", cycles: ["2026-W32"], signature: "trusted" },
    ]),
  };
}

export function accrualRequest({
  idempotencyKey = "weekly-batch-41",
  memberId = "member-41",
  cycleId = "2026-W32",
  events = [
    createAccrualEvent({ eventId: "purchase-41", cycleId: "2026-W32", points: 40 }),
    createAccrualEvent({ eventId: "review-41", cycleId: "2026-W32", points: 15 }),
  ],
} = {}) {
  return { idempotencyKey, memberId, cycleId, events };
}
