"use strict";

function assignmentKey(vesselId, day) {
  return `${vesselId}-${day}`;
}

module.exports = { assignmentKey };
