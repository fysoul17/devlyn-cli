"use strict";

function stack(id, containers, capacity, rejectedContainerIds = []) {
  return { id, containers: [...containers], capacity, rejectedContainerIds: [...rejectedContainerIds] };
}

function makeYard(overrides = {}) {
  return {
    stacks: [
      stack("A-01", ["CTR-19"], 4),
      stack("B-04", ["CTR-44"], overrides.targetCapacity ?? 3, overrides.rejectedIds ?? []),
      stack("D-02", ["CTR-17"], 4),
      stack("E-06", ["CTR-33"], 3, overrides.secondRejectedIds ?? []),
    ],
    craneLedger: [{ liftId: "lift-history", operationId: "prior-lift", containerId: "CTR-77", from: "Z-09", to: "Z-10" }],
    journal: [{ operationId: "prior-move", type: "arrival-note", containerId: "CTR-77", sourceStackId: "Z-09", targetStackId: "Z-10" }],
    completedRestacks: [],
  };
}

module.exports = { makeYard };
