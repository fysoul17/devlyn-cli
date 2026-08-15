"use strict";

function request(operationId, containerId, sourceStackId, targetStackId) {
  return { operationId, containerId, sourceStackId, targetStackId };
}

module.exports = { request };
