"use strict";

function receiptId(lotId) {
  return `RCPT-${lotId}`;
}

module.exports = { receiptId };
