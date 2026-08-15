"use strict";

function submittedReviewIds(state) {
  return state.reviewHistory.map((review) => review.id);
}

module.exports = { submittedReviewIds };
