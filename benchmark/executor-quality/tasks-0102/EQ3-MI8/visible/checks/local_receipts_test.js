"use strict";

function localCloseReceipt(result, harbor, pilotId) {
  const pilot = harbor.pilots.find((item) => item.id === pilotId);
  return result.closed === true && pilot?.status === "ready" && pilot.assignmentId === null;
}

module.exports = { localCloseReceipt };
