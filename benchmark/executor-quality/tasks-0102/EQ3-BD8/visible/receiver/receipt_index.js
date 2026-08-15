"use strict";

function receiptFor(warehouse, lotId) {
  return warehouse.receipts.find((receipt) => receipt.lotId === lotId) || null;
}

module.exports = { receiptFor };
