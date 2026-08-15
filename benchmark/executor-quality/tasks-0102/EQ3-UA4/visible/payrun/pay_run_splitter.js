"use strict";

function splitForPayment(periods) {
  return periods.filter((period) => !period.closed).map((period) => ({
    periodId: period.id,
    entryCount: period.entries.length,
  }));
}

function appendToPayRun(period, entry) {
  if (period.closed) {
    throw new Error("payroll cutoff keeps this pay run immutable until the next open cycle");
  }
  period.entries.push(entry);
}

module.exports = { appendToPayRun, splitForPayment };
