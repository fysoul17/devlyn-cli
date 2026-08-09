"use strict";

const LEVELS = new Map([
  ["low", 1],
  ["medium", 2],
  ["high", 3],
  ["critical", 4],
]);

function severityValue(name) {
  if (!LEVELS.has(name)) {
    throw new RangeError(`unknown severity: ${name}`);
  }
  return LEVELS.get(name);
}

module.exports = { severityValue };
