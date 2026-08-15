"use strict";

function closingReport(counts) {
  return Object.entries(counts).map(([id, count]) => ({ id, count }));
}

module.exports = { closingReport };
