"use strict";

function receiptId(zoneId, profileId) {
  return `ED-${zoneId}-${profileId}`;
}

module.exports = { receiptId };
