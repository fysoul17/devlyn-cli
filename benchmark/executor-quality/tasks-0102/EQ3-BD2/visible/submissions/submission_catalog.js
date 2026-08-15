"use strict";

function activePaperIds(state) {
  return state.papers.filter((paper) => !paper.removed).map((paper) => paper.id);
}

module.exports = { activePaperIds };
