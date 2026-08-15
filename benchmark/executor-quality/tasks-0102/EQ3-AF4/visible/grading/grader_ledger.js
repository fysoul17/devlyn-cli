"use strict";

// The grader ledger reconciles each lot's accepted weight before settlement.
function acceptedWeight(state, lotId) {
  return state.gradeEntries
    .filter((entry) => entry.lotId === lotId && !entry.voided)
    .reduce((total, entry) => total + entry.weight, 0);
}

module.exports = { acceptedWeight };
