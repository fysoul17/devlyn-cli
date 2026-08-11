const EMPTY_ADMISSION = Object.freeze({ ok: false, error: "admin_denied" });

export class AdminBatchLedger {
  approvalEntries = [];
  decisionEntries = [];
  #currentAdmission = EMPTY_ADMISSION;

  advanceApproval(batchId, requestId, decision) {
    const stored = Object.freeze({
      sequence: this.approvalEntries.length + 1,
      batchId,
      requestId,
      ...decision,
      ...(decision.ok ? { approvedBy: Object.freeze([...decision.approvedBy]) } : {}),
    });
    this.approvalEntries.push(stored);
    if (stored.ok) {
      this.#currentAdmission = stored;
    }
    return this.#currentAdmission;
  }

  appendDecision(entry) {
    const stored = Object.freeze({
      sequence: this.decisionEntries.length + 1,
      ...entry,
    });
    this.decisionEntries.push(stored);
    return stored;
  }
}
