export class RejectionLog {
  #entries = [];

  find(receiptId) {
    const entry = this.#entries.find((candidate) => candidate.receiptId === receiptId);
    return entry ?? null;
  }

  append(outcome) {
    const entry = Object.freeze({ ...outcome });
    this.#entries.push(entry);
    return entry;
  }

  get entries() {
    return [...this.#entries];
  }
}
