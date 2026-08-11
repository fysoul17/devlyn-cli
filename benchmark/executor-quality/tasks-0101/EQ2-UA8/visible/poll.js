export class Poll {
  #candidateIds;
  #eligibilityRoll;
  #maxChoices;
  #openPrecinctIds;

  constructor({ candidateIds, eligibilityRoll, openPrecinctIds, maxChoices = 1 }) {
    this.#candidateIds = new Set(candidateIds);
    this.#eligibilityRoll = eligibilityRoll;
    this.#maxChoices = maxChoices;
    this.#openPrecinctIds = new Set(openPrecinctIds);
  }

  rejectionsFor(ballot) {
    const rejections = [];
    let arrivalIndex = 0;

    for (const choice of ballot.choices) {
      if (!this.#candidateIds.has(choice)) {
        rejections.push({ arrivalIndex, reason: "unknown_choice", detail: choice });
        arrivalIndex += 1;
      }
    }
    if (ballot.choices.length > this.#maxChoices) {
      rejections.push({ arrivalIndex, reason: "overvote" });
      arrivalIndex += 1;
    }
    if (!this.#eligibilityRoll.includes(ballot.precinctId, ballot.voterId)) {
      rejections.push({ arrivalIndex, reason: "ineligible" });
      arrivalIndex += 1;
    }
    if (!this.#openPrecinctIds.has(ballot.precinctId)) {
      rejections.push({ arrivalIndex, reason: "poll_closed" });
    }
    return rejections;
  }
}
