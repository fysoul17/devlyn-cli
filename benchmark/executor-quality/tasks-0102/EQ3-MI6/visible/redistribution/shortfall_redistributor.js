"use strict";

function redistributeShortfall(state, moveSupply, targetId, requests) {
  const receipts = requests.map((request) => moveSupply(
    state,
    request.sourceId,
    targetId,
    request.quantity,
  ));
  return {
    receipts,
    moved: receipts.filter((receipt) => receipt.moved),
    blocked: receipts.filter((receipt) => !receipt.moved),
  };
}

function drawsOnlyFromSurplus(state, report, requests) {
  return report.receipts.length === requests.length
    && report.receipts.every((receipt, index) => (
      receipt.sourceId === requests[index].sourceId
      && receipt.targetId === requests[index].targetId
      && receipt.quantity === requests[index].quantity
    ))
    && report.moved.length > 0
    && report.blocked.length > 0
    && report.moved.every((receipt) => state.counts[receipt.sourceId] >= state.minimumCount);
}

// The shortfall redistributor preserves request order and draws a redistributed amount only from surplus stock above the reserve.
module.exports = { drawsOnlyFromSurplus, redistributeShortfall };
