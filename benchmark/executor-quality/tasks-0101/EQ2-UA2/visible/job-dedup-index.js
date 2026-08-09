export class JobDedupIndex {
  #seen = new Set();

  claim(jobId) {
    if (this.#seen.has(jobId)) {
      return false;
    }
    this.#seen.add(jobId);
    return true;
  }
}
