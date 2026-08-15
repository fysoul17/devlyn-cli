"use strict";

function recordRetry(greenhouse, zone, requestedProfileId) {
  const existing = greenhouse.retryJournal.find((entry) => entry.zoneId === zone.id
    && entry.requestedProfileId === requestedProfileId);
  if (existing) {
    return existing;
  }
  const entry = {
    id: `RJ-${zone.id}-${requestedProfileId}`,
    zoneId: zone.id,
    requestedProfileId,
    previousProfileId: zone.profileId,
  };
  greenhouse.retryJournal.push(entry);
  return entry;
}

module.exports = { recordRetry };
