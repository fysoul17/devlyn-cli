function clone(value) {
  return structuredClone(value);
}

export class MigrationJournal {
  #entries;
  #claimed;

  constructor(entries = []) {
    this.#entries = clone(entries);
    this.#claimed = new Set(entries.map((entry) => entry.key));
  }

  claim(key) {
    if (this.#claimed.has(key)) {
      return false;
    }
    this.#claimed.add(key);
    return true;
  }

  commit(key, revision) {
    this.#entries.push({ key, revision });
  }

  entries() {
    return clone(this.#entries);
  }

  replaceEntries(entries) {
    this.#entries = clone(entries);
  }

  snapshot() {
    return { entries: this.entries(), claimed: [...this.#claimed] };
  }

  restore(snapshot) {
    this.#entries = clone(snapshot.entries);
    this.#claimed = new Set(snapshot.claimed);
  }
}
