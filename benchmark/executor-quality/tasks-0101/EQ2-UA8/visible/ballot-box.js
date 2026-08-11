export class BallotBox {
  #ballots = [];
  #outcomes = new Map();

  #key(ballot) {
    return `${ballot.receiptId}:${ballot.voterId}`;
  }

  find(ballot) {
    return this.#outcomes.get(this.#key(ballot)) ?? null;
  }

  deposit(ballot) {
    const existing = this.find(ballot);
    if (existing !== null) {
      return existing;
    }

    const outcome = Object.freeze({
      receiptId: ballot.receiptId,
      voterId: ballot.voterId,
      status: "accepted",
    });
    this.#ballots.push(ballot);
    this.#outcomes.set(this.#key(ballot), outcome);
    return outcome;
  }

  get ballots() {
    return [...this.#ballots];
  }
}
