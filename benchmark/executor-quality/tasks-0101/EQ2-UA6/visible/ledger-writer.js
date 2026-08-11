export class LedgerWriter {
  constructor(accountBook, journal, { nextSequence = 1 } = {}) {
    this.accountBook = accountBook;
    this.journal = journal;
    this.nextSequence = nextSequence;
  }

  write(transfer) {
    const sequence = this.nextSequence;
    this.accountBook.debit(transfer.fromAccount, transfer.amountCents, transfer.id);
    this.accountBook.credit(transfer.toAccount, transfer.amountCents, transfer.id);
    this.journal.append({
      sequence,
      transferId: transfer.id,
      debitAccount: transfer.fromAccount,
      creditAccount: transfer.toAccount,
      amountCents: transfer.amountCents,
    });
    this.nextSequence += 1;
    return sequence;
  }

  snapshot() {
    return {
      balances: this.accountBook.snapshot(),
      journal: this.journal.snapshot(),
      nextSequence: this.nextSequence,
    };
  }

  restore(snapshot) {
    this.accountBook.restore(snapshot.balances);
    this.journal.restore(snapshot.journal);
    this.nextSequence = snapshot.nextSequence;
  }
}
