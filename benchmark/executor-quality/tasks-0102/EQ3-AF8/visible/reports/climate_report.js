"use strict";

function climateSummary(greenhouse) {
  return greenhouse.zones.map((zone) => ({ id: zone.id, profileId: zone.profileId }));
}

module.exports = { climateSummary };
