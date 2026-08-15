"use strict";

const { makeYard } = require("../yard/yard_state");
const { layoutSnapshot } = require("../yard/stack_lookup");
const { restackContainer } = require("../planner/stack_planner");

function fullTargetFailureRetainsContainer() {
  const yard = makeYard({ targetCapacity: 1 });
  const before = JSON.stringify(layoutSnapshot(yard));
  const result = restackContainer(yard, {
    operationId: "LOCAL-FULL-1", containerId: "CTR-19", sourceStackId: "A-01", targetStackId: "B-04",
  });
  return result.moved === false && result.reason === "placement-rejected"
    && JSON.stringify(layoutSnapshot(yard)) === before;
}

module.exports = { fullTargetFailureRetainsContainer };
