"use strict";

const assert = require("node:assert/strict");
const { createReviewState, removeSubmittedPaper } = require("../assigner/reviewer_assigner");

function checkRepeatedRemoval() {
  const state = createReviewState();
  removeSubmittedPaper(state, "P-204");
  removeSubmittedPaper(state, "P-204");
  assert.equal(state.reviewers[0].availableSlots, 1);
  assert.equal(state.reviewers[1].availableSlots, 1);
}

module.exports = { checkRepeatedRemoval };
