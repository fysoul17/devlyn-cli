"use strict";

function sentFor(state, requestId) {
  return state.notifications.filter((entry) => entry.portRequestId === requestId);
}

module.exports = { sentFor };
