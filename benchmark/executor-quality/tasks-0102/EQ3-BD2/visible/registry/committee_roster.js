"use strict";

function activeReviewerIds(state) {
  return state.reviewers.map((reviewer) => reviewer.id);
}

module.exports = { activeReviewerIds };
