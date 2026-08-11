export class EligibilityRoll {
  #voterIds;

  constructor(voterIds) {
    this.#voterIds = new Set(voterIds);
  }

  includes(voterId) {
    return this.#voterIds.has(voterId);
  }
}
