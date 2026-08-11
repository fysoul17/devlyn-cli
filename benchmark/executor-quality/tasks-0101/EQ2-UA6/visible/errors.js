export class LedgerBatchError extends Error {
  constructor(message) {
    super(message);
    this.name = new.target.name;
  }
}

export class InsufficientFundsError extends LedgerBatchError {
  constructor(transferId) {
    super(`insufficient funds for ${transferId}`);
  }
}

export class SettlementRejectedError extends LedgerBatchError {
  constructor(batchId) {
    super(`settlement rejected ${batchId}`);
  }
}
