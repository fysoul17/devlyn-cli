"use strict";

function zoneCard(zone) {
  return `${zone.id}:${zone.profileId}:${zone.sensorState}`;
}

module.exports = { zoneCard };
