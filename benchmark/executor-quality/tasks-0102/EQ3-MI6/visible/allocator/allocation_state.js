"use strict";

function createAllocation(counts, minimumCount) {
  return {
    counts: { ...counts },
    minimumCount,
    lockedPrecincts: new Set(),
    transferLedger: [],
  };
}

function markLocked(state, precinctId) {
  state.lockedPrecincts.add(precinctId);
}

module.exports = { createAllocation, markLocked };
