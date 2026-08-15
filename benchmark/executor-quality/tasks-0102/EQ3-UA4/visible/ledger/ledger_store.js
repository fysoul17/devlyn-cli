"use strict";

function findPeriod(ledger, periodId) {
  return ledger.periods.find((period) => period.id === periodId);
}

function countEntries(ledger) {
  return ledger.periods.reduce((total, period) => total + period.entries.length, 0);
}

module.exports = { countEntries, findPeriod };
