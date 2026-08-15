"use strict";

// The candidate choice follows ordered approval records for a released pitch.
function assignReleasedPitch(festival, permit) {
  const pitch = festival.pitches.find((item) => item.id === permit.pitchId);
  if (!pitch || pitch.occupiedBy !== permit.id) {
    return null;
  }
  const requests = festival.waitlist
    .filter((request) => request.kind === permit.kind && request.status === "waiting")
    .sort((left, right) => left.sequence - right.sequence);
  const request = requests.find((item) => festival.permits.some(
    (issued) => issued.id === item.permitId && issued.status === "issued",
  ));
  if (!request) {
    return null;
  }
  pitch.occupiedBy = request.permitId;
  request.status = "placed";
  festival.permits.find((item) => item.id === request.permitId).status = "active";
  const placement = { permitId: request.permitId, pitchId: pitch.id, sourcePermitId: permit.id };
  festival.placements.push(placement);
  return placement;
}

module.exports = { assignReleasedPitch };
