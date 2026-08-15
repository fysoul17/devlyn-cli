"use strict";

function isReceived(lot) {
  return lot && lot.status === "received";
}

module.exports = { isReceived };
