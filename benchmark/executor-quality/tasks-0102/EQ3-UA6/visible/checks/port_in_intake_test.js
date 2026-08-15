"use strict";

function correctionShown(result, state, correction) {
  return result.accepted === true
    && result.correctionId === correction.id
    && state.requests.some((request) => request.desiredCarrier === correction.desiredCarrier);
}

module.exports = { correctionShown };
