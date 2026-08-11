import { CreditPostingError, DebitPostingError } from "./errors.js";

export class AccountBook {
  constructor(balances, { failOnCredit = [] } = {}) {
    this.balances = new Map(Object.entries(balances));
    this.failOnCredit = new Set(failOnCredit);
  }

  debit(accountId, amountCents, transferId) {
    const balance = this.balances.get(accountId);
    if (!Number.isSafeInteger(balance) || balance < amountCents) {
      throw new DebitPostingError(`cannot debit ${transferId}`);
    }
    this.balances.set(accountId, balance - amountCents);
  }

  credit(accountId, amountCents, transferId) {
    if (this.failOnCredit.has(transferId)) {
      throw new CreditPostingError(`cannot credit ${transferId}`);
    }
    const balance = this.balances.get(accountId);
    if (!Number.isSafeInteger(balance)) {
      throw new CreditPostingError(`unknown credit account for ${transferId}`);
    }
    this.balances.set(accountId, balance + amountCents);
  }

  snapshot() {
    return Object.fromEntries([...this.balances].sort(([left], [right]) => left.localeCompare(right)));
  }

  restore(snapshot) {
    this.balances = new Map(Object.entries(structuredClone(snapshot)));
  }
}
