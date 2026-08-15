"use strict";

function incidentSummary(receipts) {
  return receipts.filter((receipt) => !receipt.moved).map((receipt) => receipt.reason);
}

module.exports = { incidentSummary };
