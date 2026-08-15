"use strict";

function sortScans(scans) {
  return [...scans].sort((left, right) => left.scannedAt.localeCompare(right.scannedAt));
}

module.exports = { sortScans };
