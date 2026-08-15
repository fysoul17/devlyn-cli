"use strict";

function queuedBatchIds(day) {
  return day.retryQueue.slice();
}

function boardStatus(day, batchId) {
  const batch = day.batches.find((entry) => entry.id === batchId);
  return batch ? { state: batch.status, rise: batch.riseState } : null;
}

module.exports = { boardStatus, queuedBatchIds };
