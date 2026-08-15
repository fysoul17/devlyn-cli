"use strict";

function queuedCarrierIds(state) {
  return state.notifications.map((entry) => entry.portRequestId);
}

module.exports = { queuedCarrierIds };
