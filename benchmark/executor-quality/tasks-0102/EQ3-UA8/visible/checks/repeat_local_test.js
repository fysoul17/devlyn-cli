"use strict";

const { makeYard } = require("../yard/yard_state");
const { layoutSnapshot } = require("../yard/stack_lookup");
const { restackContainer } = require("../planner/stack_planner");

function repeatedFullTargetFailureIsStable() {
  const yard = makeYard({ targetCapacity: 1 });
  const before = JSON.stringify(layoutSnapshot(yard));
  const first = restackContainer(yard, {
    operationId: "LOCAL-FULL-2", containerId: "CTR-19", sourceStackId: "A-01", targetStackId: "B-04",
  });
  const second = restackContainer(yard, {
    operationId: "LOCAL-FULL-3", containerId: "CTR-19", sourceStackId: "A-01", targetStackId: "B-04",
  });
  return first.moved === false && second.moved === false && JSON.stringify(layoutSnapshot(yard)) === before;
}

module.exports = { repeatedFullTargetFailureIsStable };
