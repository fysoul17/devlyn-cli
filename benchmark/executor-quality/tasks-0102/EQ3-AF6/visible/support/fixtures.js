"use strict";

function makeProductionDay() {
  return {
    batches: [{ id: "B17", group: "butter", status: "locked", riseState: "waiting" }],
    groupCards: ["butter", "lean"],
    retryQueue: [],
    ovenSlots: [{ id: "O1", locked: true, lockedBy: "B17", lastGroup: "butter", lastFinishedAt: 10, changeoverMinutes: 18 }],
    ingredients: [
      { name: "flour", available: 7, committed: 12, loss: 2 },
      { name: "butter", available: 1, committed: 4, loss: 1 },
    ],
    failureLedger: [],
    slotReleaseLedger: [],
  };
}

module.exports = { makeProductionDay };
