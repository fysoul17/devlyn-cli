export class PrecinctTally {
  #counts = new Map();
  #decisions = new Map();

  outcomeFor(ballotId) {
    return this.#decisions.get(ballotId) ?? null;
  }

  accept(ballot) {
    const counts = this.#counts.get(ballot.precinctId) ?? new Map();
    for (const choice of ballot.choices) {
      counts.set(choice, (counts.get(choice) ?? 0) + 1);
    }
    this.#counts.set(ballot.precinctId, counts);

    const outcome = Object.freeze({
      ballotId: ballot.ballotId,
      precinctId: ballot.precinctId,
      status: "accepted",
    });
    this.#decisions.set(ballot.ballotId, outcome);
    return outcome;
  }

  totalsFor(precinctId) {
    return Object.fromEntries(this.#counts.get(precinctId) ?? []);
  }

  get processedCount() {
    return this.#decisions.size;
  }
}
