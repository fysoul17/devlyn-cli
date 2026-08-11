export class Poll {
  #candidateIds;
  #eligibilityRoll;
  #maxChoices;
  #open;

  constructor({ candidateIds, eligibilityRoll, maxChoices = 1, open = true }) {
    this.#candidateIds = new Set(candidateIds);
    this.#eligibilityRoll = eligibilityRoll;
    this.#maxChoices = maxChoices;
    this.#open = open;
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
    if (!this.#eligibilityRoll.includes(ballot.voterId)) {
      rejections.push({ arrivalIndex, reason: "ineligible" });
      arrivalIndex += 1;
    }
    if (!this.#open) {
      rejections.push({ arrivalIndex, reason: "poll_closed" });
    }
    return rejections;
  }
}
