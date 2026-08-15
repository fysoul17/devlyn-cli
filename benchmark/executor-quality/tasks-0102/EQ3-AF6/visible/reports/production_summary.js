"use strict";

function summarizeBoard(day) {
  return { queued: day.retryQueue.length, lots: day.batches.length };
}

module.exports = { summarizeBoard };
