"use strict";

function cancellationIsActive(state, request) {
  return request.status === "cancelled" && state.clock <= request.rollbackUntil;
}

module.exports = { cancellationIsActive };
