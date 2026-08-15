"use strict";

const assert = require("node:assert/strict");
const { recordPick, recordGrade, rejectLot } = require("../picking/pick_recorder");

// The rejected-lot test checks that field inventory contains returned bins after rejection, while recorded grade entries are voided.
function rejectedLotScenario() {
  const state = {
    fieldInventory: ["B-17", "B-18"],
    lots: { "L-7": { rejected: false } },
    binRecords: [],
    gradeEntries: [],
  };
  recordPick(state, { id: "B-17", lotId: "L-7", expectedWeight: 16 });
  recordPick(state, { id: "B-18", lotId: "L-7", expectedWeight: 15 });
  recordGrade(state, "B-17", 15);
  rejectLot(state, "L-7");
  assert.deepEqual(state.fieldInventory.sort(), ["B-17", "B-18"]);
  assert.equal(state.gradeEntries[0].voided, true);
}

module.exports = { rejectedLotScenario };
