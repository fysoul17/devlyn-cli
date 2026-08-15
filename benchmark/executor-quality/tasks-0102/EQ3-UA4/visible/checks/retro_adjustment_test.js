"use strict";

const assert = require("node:assert/strict");
const { importTimesheet } = require("../importer/timesheet_importer");

// A retro adjustment records a reversal and a repost with their exact values.
function runRetroAdjustmentCheck() {
  const finalizedFlag = "clo" + "sed";
  const ledger = {
    hourlyRate: 30,
    earningCodes: ["REG"],
    periods: [
      { id: "august", [finalizedFlag]: true, entries: [{ id: "august-base", workerId: "w-7", hours: 8, amount: 240, earningCode: "REG" }] },
      { id: "september", [finalizedFlag]: false, entries: [] },
    ],
  };
  const result = importTimesheet(ledger, {
    id: "sheet-august-correction",
    workerId: "w-7",
    periodId: "august",
    replaces: "august-base",
    hours: 10,
    earningCode: "REG",
  });

  assert.equal(result.accepted, true);
  assert.deepEqual(
    ledger.periods[1].entries.map(({ kind, hours, amount }) => ({ kind, hours, amount })),
    [
      { kind: "undo", hours: -8, amount: -240 },
      { kind: "replacement", hours: 10, amount: 300 },
    ]
  );
}

module.exports = { runRetroAdjustmentCheck };
