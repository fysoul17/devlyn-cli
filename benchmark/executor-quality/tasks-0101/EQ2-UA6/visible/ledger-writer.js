function addNet(netByAccount, accountId, amountCents) {
  netByAccount.set(accountId, (netByAccount.get(accountId) ?? 0) + amountCents);
}

function orderedObject(entries) {
  return Object.fromEntries([...entries].sort(([left], [right]) => left.localeCompare(right)));
}

export class LedgerWriter {
  constructor(accountBook, journal, { nextSequence = 1 } = {}) {
    this.accountBook = accountBook;
    this.journal = journal;
    this.nextSequence = nextSequence;
    this.batchNets = {};
  }

  postBatch(batchId, transfers) {
    const draftBalances = this.accountBook.draft();
    const netByAccount = new Map();
    const rows = [];
    let sequence = this.nextSequence;

    for (const transfer of transfers) {
      this.accountBook.apply(draftBalances, transfer);
      addNet(netByAccount, transfer.fromAccount, -transfer.amountCents);
      addNet(netByAccount, transfer.toAccount, transfer.amountCents);
      rows.push({
        batchId,
        sequence,
        transferId: transfer.id,
        debitAccount: transfer.fromAccount,
        creditAccount: transfer.toAccount,
        amountCents: transfer.amountCents,
      });
      sequence += 1;
    }

    const draftJournal = this.journal.prepare(batchId, rows);
    this.accountBook.commit(draftBalances);
    this.journal.commit(draftJournal);
    this.batchNets = {
      ...this.batchNets,
      [batchId]: orderedObject(netByAccount),
    };
    this.nextSequence = sequence;
    return Object.freeze({
      batchId,
      sequenceStart: rows[0]?.sequence ?? this.nextSequence,
      transferIds: Object.freeze(transfers.map((transfer) => transfer.id)),
    });
  }

  snapshot() {
    return {
      balances: this.accountBook.snapshot(),
      batchNets: orderedObject(Object.entries(structuredClone(this.batchNets))),
      journal: this.journal.snapshot(),
      nextSequence: this.nextSequence,
    };
  }
}
