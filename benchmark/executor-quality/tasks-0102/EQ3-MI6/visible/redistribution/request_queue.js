"use strict";

function queueRequest(sourceId, quantity) {
  return { sourceId, quantity };
}

module.exports = { queueRequest };
