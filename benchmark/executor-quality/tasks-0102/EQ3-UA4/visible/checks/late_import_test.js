"use strict";

const assert = require("node:assert/strict");
const { importTimesheet } = require("../importer/timesheet_importer");
const { countEntries } = require("../ledger/ledger_store");

function ledgerFixture() {
  return {
    hourlyRate: 30,
    earningCodes: ["REG", "OT"],
    periods: [
      { id: "august", closed: true, entries: [{ id: "august-base", workerId: "w-7", hours: 8, amount: 240, earningCode: "REG" }] },
      { id: "september", closed: false, entries: [] },
    ],
  };
}

function runLateImportCheck() {
  const ledger = ledgerFixture();
  const before = countEntries(ledger);
  const result = importTimesheet(ledger, {
    id: "sheet-august-correction",
    workerId: "w-7",
    periodId: "august",
    replaces: "august-base",
    hours: 10,
    earningCode: "REG",
  });
  assert.equal(result.accepted, true);
  assert.ok(countEntries(ledger) > before);
}

module.exports = { ledgerFixture, runLateImportCheck };
