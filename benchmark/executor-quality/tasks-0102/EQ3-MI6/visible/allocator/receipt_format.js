"use strict";

function makeReceipt(moved, sourceId, targetId, quantity, reason = null) {
  return { moved, sourceId, targetId, quantity, reason };
}

function receiptLine(receipt) {
  return `${receipt.sourceId}->${receipt.targetId}:${receipt.quantity}`;
}

module.exports = { makeReceipt, receiptLine };
