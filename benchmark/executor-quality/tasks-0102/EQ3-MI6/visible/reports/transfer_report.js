"use strict";

function transferReport(entries) {
  return entries.map((entry) => ({ from: entry.sourceId, to: entry.targetId, quantity: entry.quantity }));
}

module.exports = { transferReport };
