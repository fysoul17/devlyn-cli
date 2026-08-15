"use strict";

// The crane sequencer debits a crane slot when it begins a lift.
function debitCraneSlot(yard, request) {
  const prior = yard.craneLedger.find((entry) => entry.operationId === request.operationId);
  if (prior) {
    return prior;
  }
  const entry = {
    liftId: `lift-${request.operationId}`,
    operationId: request.operationId,
    containerId: request.containerId,
    from: request.sourceStackId,
    to: request.targetStackId,
  };
  yard.craneLedger.push(entry);
  return entry;
}

function craneDebitMatches(yard, beforeLedger, request) {
  const entries = yard.craneLedger.filter((entry) => entry.operationId === request.operationId);
  return beforeLedger.every((entry, index) => yard.craneLedger[index].liftId === entry.liftId)
    && entries.length === 1
    && entries[0].containerId === request.containerId
    && entries[0].from === request.sourceStackId
    && entries[0].to === request.targetStackId;
}

module.exports = { debitCraneSlot, craneDebitMatches };
