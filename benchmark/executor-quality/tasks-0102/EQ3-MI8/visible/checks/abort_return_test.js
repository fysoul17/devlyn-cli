"use strict";

// This closure handoff check confirms that a released berth is clear for a fresh arrival.
function berthHandoffIsClear(harbor, berthId) {
  const berth = harbor.berths.find((item) => item.id === berthId);
  return berth !== undefined && berth.status === "open" && berth.assignmentId === null;
}

module.exports = { berthHandoffIsClear };
