export class EligibilityRoll {
  #votersByPrecinct;

  constructor(votersByPrecinct) {
    this.#votersByPrecinct = new Map(
      Object.entries(votersByPrecinct).map(([precinctId, voterIds]) => [
        precinctId,
        new Set(voterIds),
      ]),
    );
  }

  includes(precinctId, voterId) {
    return this.#votersByPrecinct.get(precinctId)?.has(voterId) ?? false;
  }
}
