export class LedgerWriteError extends Error {
  constructor(message) {
    super(message);
    this.name = new.target.name;
  }
}

export class DebitPostingError extends LedgerWriteError {}

export class CreditPostingError extends LedgerWriteError {}

export class JournalAppendError extends LedgerWriteError {}
