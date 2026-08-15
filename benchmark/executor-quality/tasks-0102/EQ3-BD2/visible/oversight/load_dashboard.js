"use strict";

function reviewerRows(state) {
  return state.reviewers.map((reviewer) => ({
    id: reviewer.id,
    openSlots: reviewer.availableSlots,
    assignedReviews: state.loadCounts[reviewer.id],
  }));
}

module.exports = { reviewerRows };
