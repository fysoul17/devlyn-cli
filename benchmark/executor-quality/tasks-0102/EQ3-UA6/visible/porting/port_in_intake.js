"use strict";

function resubmitPortIn(state, correction, notify) {
  return { accepted: false, correctionId: correction.id };
}

module.exports = { resubmitPortIn };
