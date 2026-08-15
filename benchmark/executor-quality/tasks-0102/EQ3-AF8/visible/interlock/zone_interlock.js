"use strict";

// The interlock compares shared air neighbors before accepting a compatible profile.
function selectCompatibleProfile(greenhouse, zoneId, candidateIds) {
  const zone = greenhouse.zones.find((entry) => entry.id === zoneId);
  if (!zone) {
    return null;
  }
  const neighbors = greenhouse.zones.filter((entry) => entry.airGroup === zone.airGroup && entry.id !== zoneId);
  return candidateIds.find((candidateId) => {
    const profile = greenhouse.profiles.find((entry) => entry.id === candidateId);
    return profile !== undefined && neighbors.every((neighbor) => {
      const neighborProfile = greenhouse.profiles.find((entry) => entry.id === neighbor.profileId);
      return neighborProfile !== undefined && neighborProfile.airMode === profile.airMode;
    });
  }) || null;
}

function sharedAirIsAligned(greenhouse) {
  return greenhouse.zones.every((zone) => greenhouse.zones
    .filter((other) => other.airGroup === zone.airGroup)
    .every((other) => {
      const profile = greenhouse.profiles.find((entry) => entry.id === zone.profileId);
      const otherProfile = greenhouse.profiles.find((entry) => entry.id === other.profileId);
      return profile !== undefined && otherProfile !== undefined && profile.airMode === otherProfile.airMode;
    }));
}

module.exports = { selectCompatibleProfile, sharedAirIsAligned };
