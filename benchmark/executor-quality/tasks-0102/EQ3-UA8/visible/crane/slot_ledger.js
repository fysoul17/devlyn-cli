"use strict";

function slotsFor(yard, operationId) {
  return yard.craneLedger.filter((entry) => entry.operationId === operationId);
}

module.exports = { slotsFor };
