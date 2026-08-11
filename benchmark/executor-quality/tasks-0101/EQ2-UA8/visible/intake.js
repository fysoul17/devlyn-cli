import { chooseRejection } from "./rejection-policy.js";

function duplicateOf(outcome) {
  return Object.freeze({
    ballotId: outcome.ballotId,
    precinctId: outcome.precinctId,
    status: "duplicate",
    originalStatus: outcome.status,
    ...(outcome.reason === undefined ? {} : { reason: outcome.reason }),
  });
}

export function tabulateBatch(poll, tally, rejectionLog, ballots) {
  return ballots.map((ballot) => {
    const processed = tally.outcomeFor(ballot.ballotId);
    if (processed !== null) {
      return duplicateOf(processed);
    }

    const logged = rejectionLog.findExact(ballot);
    if (logged !== null) {
      return duplicateOf(logged);
    }

    const rejection = chooseRejection(poll.rejectionsFor(ballot));
    if (rejection !== null) {
      return rejectionLog.append(ballot, rejection);
    }

    return tally.accept(ballot);
  });
}
