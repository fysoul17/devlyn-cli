"use strict";

function createEntry(values) {
  return {
    id: values.id,
    workerId: values.workerId,
    hours: values.hours,
    amount: values.amount,
    earningCode: values.earningCode,
    sourceTimesheet: values.sourceTimesheet,
    kind: values.kind || "regular",
  };
}

module.exports = { createEntry };
