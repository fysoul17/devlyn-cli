"use strict";

const { stackById } = require("../yard/stack_lookup");
const { canPlace, placeContainer } = require("../yard/placement_rules");

function restackContainer(yard, request) {
  const source = stackById(yard, request.sourceStackId);
  const target = stackById(yard, request.targetStackId);
  if (!source || !target || source.id === target.id) {
    return { moved: false, reason: "unknown-stack", operationId: request.operationId };
  }

  const containerId = source.containers[source.containers.length - 1];
  if (containerId !== request.containerId) {
    return { moved: false, reason: "not-on-top", operationId: request.operationId };
  }

  source.containers.pop();
  try {
    placeContainer(target, containerId);
    return { moved: true, operationId: request.operationId };
  } catch (error) {
    return { moved: false, reason: "placement-rejected", operationId: request.operationId };
  }
}

module.exports = { restackContainer };
