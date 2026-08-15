"use strict";

function countBins(binIds) {
  return new Set(binIds).size;
}

module.exports = { countBins };
