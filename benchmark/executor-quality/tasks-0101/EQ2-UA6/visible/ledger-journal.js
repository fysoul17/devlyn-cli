import { JournalAppendError } from "./errors.js";

export class LedgerJournal {
  constructor(rows = [], { failAfterAppend = [] } = {}) {
    this.rows = structuredClone(rows);
    this.failAfterAppend = new Set(failAfterAppend);
  }

  append(row) {
    this.rows.push(structuredClone(row));
    if (this.failAfterAppend.has(row.transferId)) {
      throw new JournalAppendError(`cannot append ${row.transferId}`);
    }
  }

  snapshot() {
    return structuredClone(this.rows);
  }

  restore(snapshot) {
    this.rows = structuredClone(snapshot);
  }
}
