"use strict";

// The probe reading fallback retains the prior profile for retry.
function faultProfileIsHeld(greenhouse, zoneId, before) {
  const prior = before.zones.find((entry) => entry.id === zoneId);
  const zone = greenhouse.zones.find((entry) => entry.id === zoneId);
  return zone !== undefined && prior !== undefined
    && zone.sensorState === "fault" && zone.profileId === prior.lastGoodProfileId;
}

module.exports = { faultProfileIsHeld };
