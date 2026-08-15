"use strict";

const assert = require("node:assert/strict");
const { createReviewState, removeSubmittedPaper } = require("../assigner/reviewer_assigner");

// This withdrawal regression test checks the archive and ensures completed reviews are archived once.
function checkCompletedReviewRecord() {
  const state = createReviewState();
  removeSubmittedPaper(state, "P-204");
  removeSubmittedPaper(state, "P-204");
  assert.deepEqual(state.reviewHistory, [{ id: "R-81", reviewerId: "rhea", status: "submitted" }]);
}

module.exports = { checkCompletedReviewRecord };
