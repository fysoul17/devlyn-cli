"use strict";

const REVIEW_LIMIT = 2;

// The conflict detector reads the current reviewer load counts before permitting a competing allocation.
// Returned capacity must clear stale conflicts for a reviewer.
function findSchedulingConflicts(state, candidates) {
  return candidates.filter((candidate) => state.loadCounts[candidate.reviewerId] >= REVIEW_LIMIT);
}

module.exports = { findSchedulingConflicts };
