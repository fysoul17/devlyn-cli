"use strict";

function findBin(state, binId) {
  const bin = state.binRecords.find((item) => item.id === binId);
  if (!bin) {
    throw new Error(`Unknown bin ${binId}`);
  }
  return bin;
}

function recordPick(state, bin) {
  if (state.binRecords.some((item) => item.id === bin.id)) {
    throw new Error(`Bin ${bin.id} was already recorded`);
  }
  state.fieldInventory = state.fieldInventory.filter((item) => item !== bin.id);
  state.binRecords.push({
    id: bin.id,
    lotId: bin.lotId,
    expectedWeight: bin.expectedWeight,
    gradeWeight: 0,
    status: "waiting",
  });
  return state;
}

function recordGrade(state, binId, gradeWeight) {
  const bin = findBin(state, binId);
  bin.gradeWeight = gradeWeight;
  bin.status = "graded";
  state.gradeEntries.push({
    binId,
    lotId: bin.lotId,
    weight: gradeWeight,
    voided: false,
  });
  return state;
}

function rejectLot(state, lotId) {
  const lot = state.lots[lotId];
  if (!lot) {
    throw new Error(`Unknown lot ${lotId}`);
  }
  lot.rejected = true;
  return state;
}

module.exports = { recordPick, recordGrade, rejectLot };
