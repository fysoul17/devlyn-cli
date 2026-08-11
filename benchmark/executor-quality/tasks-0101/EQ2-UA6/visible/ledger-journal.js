import { SettlementRejectedError } from "./errors.js";

export class LedgerJournal {
  constructor(rows = [], { blockedBatchIds = [] } = {}) {
    this.rows = structuredClone(rows);
    this.blockedBatchIds = new Set(blockedBatchIds);
  }

  prepare(batchId, rows) {
    if (this.blockedBatchIds.has(batchId)) {
      throw new SettlementRejectedError(batchId);
    }
    return [...structuredClone(this.rows), ...structuredClone(rows)];
  }

  commit(rows) {
    this.rows = structuredClone(rows);
  }

  allowBatch(batchId) {
    this.blockedBatchIds.delete(batchId);
  }

  snapshot() {
    return structuredClone(this.rows);
  }
}
