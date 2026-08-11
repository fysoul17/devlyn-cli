function decisionEntry(batchId, row) {
  if (row.ok) {
    return {
      batchId,
      requestId: row.requestId,
      outcome: "applied",
      revision: row.revision,
    };
  }
  if (row.error === "admin_denied") {
    return {
      batchId,
      requestId: row.requestId,
      outcome: "denied",
      error: row.error,
    };
  }
  return {
    batchId,
    requestId: row.requestId,
    outcome: "rejected",
    error: row.error,
    reason: row.reason,
  };
}

export class AdminGate {
  constructor(approvals, writer, ledger) {
    this.approvals = approvals;
    this.writer = writer;
    this.ledger = ledger;
  }

  applyBatch(batch) {
    const results = [];
    for (const request of batch.requests) {
      const decision = this.approvals.authorize(request.approvalIds, request.tier);
      const admission = this.ledger.advanceApproval(batch.id, request.id, decision);
      const outcome = this.writer.apply(request.change, admission);
      const row = Object.freeze({ requestId: request.id, ...outcome });
      results.push(row);
      this.ledger.appendDecision(decisionEntry(batch.id, row));
    }
    return {
      ok: results.every((result) => result.ok),
      batchId: batch.id,
      results,
    };
  }
}
