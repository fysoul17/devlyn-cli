import { ApprovalDirectory } from "./admin-auth.js";
import { AdminGate } from "./admin-gate.js";
import { LimitConfigStore } from "./config-store.js";
import { AdminBatchLedger } from "./decision-ledger.js";
import { LimitValidationJournal, LimitWriter } from "./limit-writer.js";

export function createRateLimitFixture() {
  const store = new LimitConfigStore();
  const validations = new LimitValidationJournal();
  const ledger = new AdminBatchLedger();
  const approvals = new ApprovalDirectory([
    { id: "operator-north", role: "operator", active: true, tiers: ["edge", "core"] },
    { id: "operator-south", role: "operator", active: true, tiers: ["edge"] },
    { id: "security-edge", role: "security", active: true, tiers: ["edge"] },
    { id: "security-core", role: "security", active: true, tiers: ["edge", "core"] },
    { id: "security-retired", role: "security", active: false, tiers: ["edge", "core"] },
  ]);
  const writer = new LimitWriter(store, validations);
  return {
    gate: new AdminGate(approvals, writer, ledger),
    writer,
    store,
    validations,
    ledger,
  };
}

export function validChange(overrides = {}) {
  return {
    id: "change-edge-defaults",
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
    tier: "edge",
    approvalIds: ["operator-north", "security-edge"],
    change: validChange(),
    ...overrides,
  };
}

export function validBatch(requests = [validRequest()], id = "batch-default") {
  return { id, requests };
}
