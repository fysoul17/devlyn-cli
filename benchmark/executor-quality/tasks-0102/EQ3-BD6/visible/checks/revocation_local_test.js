"use strict";

function revocationShown(festival, permitId) {
  return !festival.permits.some((permit) => permit.id === permitId && permit.status === "active");
}

module.exports = { revocationShown };
