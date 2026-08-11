function denied(transfer, reason) {
  return { transfer, authorized: false, reason };
}

export class MandateCheck {
  constructor(mandates) {
    this.mandates = structuredClone(mandates);
  }

  reviewTransfer(transfer, effectiveDate) {
    const mandate = this.mandates[transfer.mandateId];
    if (!mandate) {
      return denied(transfer, "missing-mandate");
    }
    if (mandate.status !== "active") {
      return denied(transfer, mandate.status);
    }
    if (effectiveDate > mandate.expiresOn) {
      return denied(transfer, "expired");
    }
    if (mandate.debitAccount !== transfer.fromAccount) {
      return denied(transfer, "debit-scope");
    }
    if (mandate.currency !== transfer.currency) {
      return denied(transfer, "currency-scope");
    }
    if (transfer.amountCents > mandate.remainingCents) {
      return denied(transfer, "allowance");
    }
    return { transfer, authorized: true, reason: null };
  }

  reviewBatch(transfers, effectiveDate) {
    const usedByMandate = new Map();
    return transfers.map((transfer) => {
      const decision = this.reviewTransfer(transfer, effectiveDate);
      if (!decision.authorized) {
        return decision;
      }
      const used = (usedByMandate.get(transfer.mandateId) ?? 0) + transfer.amountCents;
      if (used > this.mandates[transfer.mandateId].remainingCents) {
        return denied(transfer, "batch-allowance");
      }
      usedByMandate.set(transfer.mandateId, used);
      return decision;
    });
  }
}
