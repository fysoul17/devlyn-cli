"use strict";

function makeRoute() {
  return {
    stops: [
      { id: "oak", kind: "paper", units: 2 },
      { id: "pine", kind: "glass", units: 2 },
      { id: "elm", kind: "paper", units: 2 },
    ],
    followups: [{ id: "retry-oak", stopId: "oak", kind: "paper", units: 2 }],
    moves: [],
    depotRebalanceLedger: [],
  };
}

module.exports = { makeRoute };
