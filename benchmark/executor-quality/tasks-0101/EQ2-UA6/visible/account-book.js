import { InsufficientFundsError } from "./errors.js";

export class AccountBook {
  constructor(balances) {
    this.balances = new Map(Object.entries(balances));
  }

  draft() {
    return new Map(this.balances);
  }

  apply(draft, transfer) {
    const debitBalance = draft.get(transfer.fromAccount);
    const creditBalance = draft.get(transfer.toAccount);
    if (!Number.isSafeInteger(debitBalance) || debitBalance < transfer.amountCents) {
      throw new InsufficientFundsError(transfer.id);
    }
    if (!Number.isSafeInteger(creditBalance)) {
      throw new InsufficientFundsError(transfer.id);
    }
    draft.set(transfer.fromAccount, debitBalance - transfer.amountCents);
    draft.set(transfer.toAccount, creditBalance + transfer.amountCents);
  }

  commit(draft) {
    this.balances = new Map(draft);
  }

  snapshot() {
    return Object.fromEntries([...this.balances].sort(([left], [right]) => left.localeCompare(right)));
  }
}
