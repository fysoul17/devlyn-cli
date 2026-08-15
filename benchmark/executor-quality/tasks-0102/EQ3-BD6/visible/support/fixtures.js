"use strict";

function makeFestival() {
  return {
    permits: [
      { id: "F-41", pitchId: "E4", kind: "food", status: "active", feeCents: 910, validDays: 14, setupDay: 2 },
      { id: "P-52", pitchId: null, kind: "food", status: "issued", feeCents: 730, validDays: 14, setupDay: 2 },
      { id: "P-63", pitchId: null, kind: "food", status: "issued", feeCents: 680, validDays: 14, setupDay: 2 },
    ],
    pitches: [{ id: "E4", occupiedBy: "F-41" }],
    waitlist: [
      { permitId: "P-63", kind: "food", status: "waiting", sequence: 19 },
      { permitId: "P-52", kind: "food", status: "waiting", sequence: 4 },
    ],
    placements: [],
    creditEntries: [{ id: "CR-old", permitId: "F-10", amountCents: 111, remainingDays: 1 }],
  };
}

module.exports = { makeFestival };
