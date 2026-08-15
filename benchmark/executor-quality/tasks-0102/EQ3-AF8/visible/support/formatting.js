"use strict";

function formatZone(zone) {
  return `${zone.id} ${zone.profileId}`;
}

module.exports = { formatZone };
