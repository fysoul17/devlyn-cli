"use strict";

function findBatch(day, batchId) {
  const batch = day.batches.find((entry) => entry.id === batchId);
  if (!batch) {
    throw new Error("Unknown batch");
  }
  return batch;
}

function failRise(day, batchId) {
  findBatch(day, batchId);
  return { requeued: false, batchId };
}

module.exports = { failRise, findBatch };
