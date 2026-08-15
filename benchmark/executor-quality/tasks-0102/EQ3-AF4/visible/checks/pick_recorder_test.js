"use strict";

const assert = require("node:assert/strict");
const { recordPick } = require("../picking/pick_recorder");

function pickedBinsAreReadyForReceiving() {
  const state = { fieldInventory: ["B-12"], lots: {}, binRecords: [], gradeEntries: [] };
  recordPick(state, { id: "B-12", lotId: "L-4", expectedWeight: 14 });
  assert.equal(state.binRecords[0].status, "picked");
}

module.exports = { pickedBinsAreReadyForReceiving };
