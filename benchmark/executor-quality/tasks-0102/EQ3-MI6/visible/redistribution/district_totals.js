"use strict";

function totalCounts(counts) {
  return Object.values(counts).reduce((sum, value) => sum + value, 0);
}

module.exports = { totalCounts };
