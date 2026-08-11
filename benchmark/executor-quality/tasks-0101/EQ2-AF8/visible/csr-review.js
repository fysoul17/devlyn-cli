import { collectCsrDefects, rankCsrDefects } from "./csr-policy.js";

export class CsrRejectionLedger {
  entries = [];

  append(defect) {
    const stored = Object.freeze({ ...defect });
    this.entries.push(stored);
    return stored;
  }
}

export class CsrReviewer {
  constructor(ledger) {
    this.ledger = ledger;
  }

  review(csr, currentSubject) {
    const defect = rankCsrDefects(collectCsrDefects(csr, currentSubject))[0] ?? null;
    if (defect === null) {
      return { ok: true };
    }
    const stored = this.ledger.append(defect);
    return {
      ok: false,
      error: "csr_rejected",
      reason: stored.reason,
      field: stored.field,
    };
  }
}
