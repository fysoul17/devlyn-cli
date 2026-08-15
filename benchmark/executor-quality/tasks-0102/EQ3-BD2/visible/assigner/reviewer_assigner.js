"use strict";

function createReviewState() {
  return {
    reviewers: [
      { id: "rhea", availableSlots: 0 },
      { id: "tomas", availableSlots: 0 },
    ],
    loadCounts: { rhea: 2, tomas: 1 },
    papers: [
      {
        id: "P-204",
        removed: false,
        reviewerIds: ["rhea", "tomas"],
        reviews: [
          { id: "R-81", reviewerId: "rhea", status: "submitted" },
          { id: "R-82", reviewerId: "tomas", status: "in-progress" },
        ],
      },
    ],
    reviewHistory: [],
  };
}

function removeSubmittedPaper(state, paperId) {
  const paper = state.papers.find((item) => item.id === paperId);
  if (!paper || paper.removed) {
    return state;
  }
  paper.removed = true;
  return state;
}

module.exports = { createReviewState, removeSubmittedPaper };
