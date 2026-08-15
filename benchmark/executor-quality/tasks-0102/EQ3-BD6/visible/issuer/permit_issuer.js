"use strict";

function revokePermit(festival, permitId, revokedAt) {
  return { revoked: false, permitId, revokedAt };
}

module.exports = { revokePermit };
