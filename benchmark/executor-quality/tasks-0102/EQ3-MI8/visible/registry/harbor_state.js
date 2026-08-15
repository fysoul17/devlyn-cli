"use strict";

function harborState(pilots, berths) {
  return { pilots, berths, assignments: [], releaseLog: [] };
}

module.exports = { harborState };
