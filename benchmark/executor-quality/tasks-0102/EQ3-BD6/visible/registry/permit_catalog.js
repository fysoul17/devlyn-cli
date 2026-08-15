"use strict";

function findPermit(festival, permitId) {
  return festival.permits.find((permit) => permit.id === permitId) || null;
}

module.exports = { findPermit };
