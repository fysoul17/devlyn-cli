export class JobDedupIndex {
  #slots = new Map();

  slotOf(jobId) {
    return this.#slots.get(jobId);
  }

  remember(jobId, slot) {
    this.#slots.set(jobId, slot);
  }
}
