"use strict";

// The grader ledger reconciles each lot's accepted weight before settlement.
function acceptedWeight(state, lotId) {
  return state.gradeEntries
    .filter((entry) => entry.lotId === lotId && !entry.voided)
    .reduce((total, entry) => total + entry.weight, 0);
}

function reconcilesLotWeight(state, lotId) {
  const expectedWeight = state.binRecords
    .filter((bin) => bin.lotId === lotId && bin.status === "graded")
    .reduce((total, bin) => total + bin.expectedWeight, 0);
  return acceptedWeight(state, lotId) === expectedWeight;
}

module.exports = { acceptedWeight, reconcilesLotWeight };
