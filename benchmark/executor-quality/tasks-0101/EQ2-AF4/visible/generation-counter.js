function clone(value) {
  return structuredClone(value);
}

export class GenerationCounter {
  #generations;
  #completed;

  constructor(generations = {}, completed = []) {
    this.#generations = clone(generations);
    this.#completed = new Set(completed);
  }

  hasCompleted(batchId) {
    return this.#completed.has(batchId);
  }

  next(scope) {
    const generation = (this.#generations[scope] ?? 0) + 1;
    this.#generations[scope] = generation;
    return generation;
  }

  complete(batchId) {
    this.#completed.add(batchId);
  }

  snapshot() {
    return {
      generations: clone(this.#generations),
      completed: [...this.#completed],
    };
  }

  restore(snapshot) {
    this.#generations = clone(snapshot.generations);
    this.#completed = new Set(snapshot.completed);
  }

  view() {
    return this.snapshot();
  }
}
