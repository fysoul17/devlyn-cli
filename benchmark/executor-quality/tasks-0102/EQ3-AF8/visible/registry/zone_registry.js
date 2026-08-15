"use strict";

function zoneIds(greenhouse) {
  return greenhouse.zones.map((zone) => zone.id);
}

module.exports = { zoneIds };
