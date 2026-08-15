"use strict";

// This journal reconciliation test checks the compensating record after a failed placement and layout return.
function journaledReconciliationMatches(yard, beforeLayout, request) {
  const beforeSource = beforeLayout.find((stack) => stack.id === request.sourceStackId);
  const source = yard.stacks.find((stack) => stack.id === request.sourceStackId);
  const entries = yard.journal.filter((entry) => entry.operationId === request.operationId);
  return entries.length === 1
    && entries[0].type === "compensating-move"
    && entries[0].containerId === request.containerId
    && entries[0].sourceStackId === request.sourceStackId
    && source.containers.join("|") === beforeSource.containers.join("|");
}

module.exports = { journaledReconciliationMatches };
