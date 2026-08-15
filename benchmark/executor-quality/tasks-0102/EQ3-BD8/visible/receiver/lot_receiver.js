"use strict";

function receiveLot(warehouse, lotId, receivedAt) {
  return { accepted: false, lotId, receivedAt };
}

function recordSampleFailure(warehouse, lotId, failedAt) {
  return { closed: false, lotId, failedAt };
}

module.exports = { receiveLot, recordSampleFailure };
