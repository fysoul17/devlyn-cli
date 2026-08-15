"use strict";

const { createEntry } = require("./entry_builder");

function hasUsableFields(sheet) {
  return Boolean(
    sheet && sheet.id && sheet.workerId && sheet.periodId &&
    Number.isFinite(sheet.hours) && sheet.hours > 0 && sheet.earningCode
  );
}

function importTimesheet(ledger, sheet) {
  if (!hasUsableFields(sheet)) {
    return { accepted: false, reason: "invalid timesheet" };
  }
  const period = ledger.periods.find((item) => item.id === sheet.periodId);
  if (!period || period.closed || !ledger.earningCodes.includes(sheet.earningCode)) {
    return { accepted: false, reason: "period unavailable" };
  }
  period.entries.push(createEntry({
    id: sheet.id,
    workerId: sheet.workerId,
    hours: sheet.hours,
    amount: sheet.hours * ledger.hourlyRate,
    earningCode: sheet.earningCode,
    sourceTimesheet: sheet.id,
  }));
  return { accepted: true, id: sheet.id };
}

module.exports = { importTimesheet };
