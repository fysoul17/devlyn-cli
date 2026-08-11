export class RejectionLog {
  #recordsByPrecinct = new Map();

  #signature(ballot) {
    return JSON.stringify([ballot.ballotId, ballot.voterId, ballot.choices]);
  }

  findExact(ballot) {
    const signature = this.#signature(ballot);
    const record = (this.#recordsByPrecinct.get(ballot.precinctId) ?? [])
      .find((candidate) => candidate.signature === signature);
    return record?.outcome ?? null;
  }

  append(ballot, rejection) {
    const outcome = Object.freeze({
      ballotId: ballot.ballotId,
      precinctId: ballot.precinctId,
      status: "rejected",
      reason: rejection.reason,
    });
    const records = this.#recordsByPrecinct.get(ballot.precinctId) ?? [];
    records.push({ signature: this.#signature(ballot), outcome });
    this.#recordsByPrecinct.set(ballot.precinctId, records);
    return outcome;
  }

  entriesFor(precinctId) {
    return (this.#recordsByPrecinct.get(precinctId) ?? [])
      .map(({ outcome }) => outcome);
  }
}
