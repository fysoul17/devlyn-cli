"use strict";

function isReadyForPayment(period) {
  return !period.closed && period.entries.every((entry) => entry.amount !== 0);
}

module.exports = { isReadyForPayment };
