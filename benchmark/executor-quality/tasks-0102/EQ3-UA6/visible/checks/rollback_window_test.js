"use strict";

// A rollback window requires the original number mapping before a correction continues.
function matchesOriginalMapping(state, request) {
  const mapped = state.numberMap[request.number];
  return state.clock <= request.rollbackUntil
    && mapped.subscriptionId === request.originalMapping.subscriptionId
    && mapped.carrier === request.originalMapping.carrier
    && mapped.route === request.originalMapping.route;
}

module.exports = { matchesOriginalMapping };
