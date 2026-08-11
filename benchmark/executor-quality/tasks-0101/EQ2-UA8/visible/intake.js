import { chooseRejection } from "./rejection-policy.js";

export function receiveBallot(poll, ballotBox, rejectionLog, ballot) {
  const accepted = ballotBox.find(ballot);
  if (accepted !== null) {
    return accepted;
  }

  const rejection = chooseRejection(poll.rejectionsFor(ballot));
  if (rejection !== null) {
    return rejectionLog.append({
      receiptId: ballot.receiptId,
      voterId: ballot.voterId,
      status: "rejected",
      reason: rejection.reason,
    });
  }

  return ballotBox.deposit(ballot);
}
