"use strict";

function findZone(greenhouse, zoneId) {
  const zone = greenhouse.zones.find((entry) => entry.id === zoneId);
  if (!zone) {
    throw new Error("Unknown zone");
  }
  return zone;
}

function updateSetpoint(greenhouse, zoneId, profileId) {
  return { updated: false, zoneId, profileId };
}

module.exports = { findZone, updateSetpoint };
