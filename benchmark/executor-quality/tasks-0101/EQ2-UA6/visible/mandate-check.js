export class MandateCheck {
  constructor(mandates) {
    this.mandates = structuredClone(mandates);
  }

  review(transfers) {
    return transfers.map((transfer) => {
      const mandate = this.mandates[transfer.mandateId];
      if (!mandate) {
        return { transfer, authorized: false, reason: "missing-mandate" };
      }
      if (mandate.status !== "active") {
        return { transfer, authorized: false, reason: mandate.status };
      }
      if (
        mandate.debitAccount !== transfer.fromAccount ||
        transfer.amountCents > mandate.limitCents
      ) {
        return { transfer, authorized: false, reason: "mandate-scope" };
      }
      return { transfer, authorized: true, reason: null };
    });
  }
}
