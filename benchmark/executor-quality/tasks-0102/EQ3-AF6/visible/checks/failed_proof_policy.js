"use strict";

// A failed proof returns committed stock adjusted for waste and records a released oven slot.
function proofStockIsSettled(day, batchId, before) {
  const batch = day.batches.find((entry) => entry.id === batchId);
  const settled = day.ingredients.every((item) => {
    const original = before.find((entry) => entry.name === item.name);
    return item.committed === 0 && item.available === original.available + original.committed - original.loss;
  });
  return settled
    && day.failureLedger.filter((entry) => entry.batchId === batchId).length === 1
    && day.slotReleaseLedger.filter((entry) => entry.batchId === batchId).length === 1
    && batch.riseState === "failed";
}

module.exports = { proofStockIsSettled };
