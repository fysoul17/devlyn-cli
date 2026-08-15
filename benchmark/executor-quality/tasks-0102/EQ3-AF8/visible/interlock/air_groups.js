"use strict";

function groupZones(greenhouse, groupId) {
  return greenhouse.zones.filter((zone) => zone.airGroup === groupId);
}

module.exports = { groupZones };
