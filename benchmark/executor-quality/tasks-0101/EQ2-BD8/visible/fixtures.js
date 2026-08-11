import { ApprovalDirectory } from "./admin-auth.js";
import { AdminGate } from "./admin-gate.js";
import { LimitConfigStore } from "./config-store.js";
import { AdminDecisionLedger } from "./decision-ledger.js";
import { LimitRejectionLog, LimitWriter } from "./limit-writer.js";

export function createRateLimitFixture() {
  const store = new LimitConfigStore();
  const rejections = new LimitRejectionLog();
  const decisions = new AdminDecisionLedger();
  const approvals = new ApprovalDirectory([
    { id: "approval-east", active: true, tiers: ["edge", "core"] },
    { id: "approval-west", active: true, tiers: ["edge"] },
    { id: "approval-retired", active: false, tiers: ["edge", "core"] },
  ]);
  const writer = new LimitWriter(store, rejections);
  return {
    gate: new AdminGate(approvals, writer, decisions),
    writer,
    store,
    rejections,
    decisions,
  };
}

export function validChange(overrides = {}) {
  return {
    id: "change-edge-defaults",
    tier: "edge",
    rules: [
      { bucket: "anonymous", windowMs: 1_000, limit: 20 },
      { bucket: "member", windowMs: 60_000, limit: 600 },
    ],
    ...overrides,
  };
}

export function validRequest(overrides = {}) {
  return {
    id: "request-edge-defaults",
    approvalIds: ["approval-east", "approval-west"],
    change: validChange(),
    ...overrides,
  };
}
