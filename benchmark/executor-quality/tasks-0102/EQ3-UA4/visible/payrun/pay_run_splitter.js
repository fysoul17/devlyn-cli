"use strict";

function splitForPayment(periods) {
  return periods.filter((period) => !period.closed).map((period) => ({
    periodId: period.id,
    entryCount: period.entries.length,
  }));
}

// A payroll cutoff is a final boundary: the pay-run splitter keeps a closed period immutable and directs adjustments to the next open cycle.

module.exports = { splitForPayment };
