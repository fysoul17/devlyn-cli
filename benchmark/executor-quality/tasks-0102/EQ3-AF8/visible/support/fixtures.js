"use strict";

function makeGreenhouse(options = {}) {
  const targetId = options.targetId || "A1";
  const peerId = options.peerId || "B2";
  const safeId = options.safeId || "dawn";
  const requestedId = options.requestedId || "mist";
  const alternateId = options.alternateId || "shade";
  const group = options.group || "east";
  const sensorState = options.sensorState || "fault";
  return {
    zones: [
      { id: targetId, profileId: safeId, lastGoodProfileId: safeId, sensorState, airGroup: group },
      { id: peerId, profileId: safeId, lastGoodProfileId: safeId, sensorState: "ready", airGroup: group },
    ],
    profiles: [
      { id: safeId, airMode: "dry" },
      { id: requestedId, airMode: "humid" },
      { id: alternateId, airMode: "dry" },
    ],
    retryJournal: [{ id: "RJ-old", zoneId: "old", requestedProfileId: "old", previousProfileId: "keep" }],
    editReceipts: [],
  };
}

module.exports = { makeGreenhouse };
