"use strict";

const { makeReceipt } = require("./receipt_format");

function moveSupply(state, sourceId, targetId, quantity) {
  return makeReceipt(false, sourceId, targetId, quantity, "pending");
}

module.exports = { moveSupply };
