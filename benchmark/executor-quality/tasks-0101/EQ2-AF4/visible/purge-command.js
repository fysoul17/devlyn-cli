export class PurgeCommand {
  #preparedGeneration;

  constructor(scope, { failAfterPurge = false } = {}) {
    this.scope = scope;
    this.failAfterPurge = failAfterPurge;
    this.#preparedGeneration = null;
  }

  prepare(counter) {
    if (this.#preparedGeneration === null) {
      this.#preparedGeneration = counter.next(this.scope);
    }
    return this.#preparedGeneration;
  }

  execute(store, generation) {
    const removed = store.purge(this.scope, generation);
    if (this.failAfterPurge) {
      throw new Error(`purge failed for scope: ${this.scope}`);
    }
    return removed;
  }

  preparation() {
    return this.#preparedGeneration;
  }

  restorePreparation(generation) {
    this.#preparedGeneration = generation;
  }
}
