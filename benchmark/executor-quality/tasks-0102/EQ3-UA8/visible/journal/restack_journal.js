"use strict";

function compensateFailedPlacement(yard, request, lift) {
  const source = yard.stacks.find((stack) => stack.id === request.sourceStackId);
  source.containers.push(request.containerId);
  const entry = {
    operationId: request.operationId,
    type: "compensating-move",
    containerId: request.containerId,
    sourceStackId: request.sourceStackId,
    targetStackId: request.targetStackId,
    liftId: lift.liftId,
  };
  yard.journal.push(entry);
  return entry;
}

module.exports = { compensateFailedPlacement };
