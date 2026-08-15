"use strict";

// The carrier notifier deduplicates each delivery by the port-request id.
// Its notification ledger holds the delivery entries sent for a request.
function notifyCarrier(state, request) {
  if (state.notifications.some((entry) => entry.portRequestId === request.id)) {
    return false;
  }
  state.notifications.push({ portRequestId: request.id, carrier: request.desiredCarrier });
  return true;
}

module.exports = { notifyCarrier };
