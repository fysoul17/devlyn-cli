function clone(value) {
  return structuredClone(value);
}

export class CacheStore {
  #entries;

  constructor(entries = []) {
    this.#entries = clone(entries);
  }

  purge(scope, cutoff) {
    const removed = [];
    this.#entries = this.#entries.filter((entry) => {
      if (entry.scope === scope && entry.generation < cutoff) {
        removed.push(entry.key);
        return false;
      }
      return true;
    });
    return removed;
  }

  snapshot() {
    return clone(this.#entries);
  }

  restore(entries) {
    this.#entries = clone(entries);
  }

  view() {
    return this.snapshot();
  }
}
