"use strict";

function occupiedPitchIds(festival) {
  return festival.pitches.filter((pitch) => pitch.occupiedBy).map((pitch) => pitch.id);
}

module.exports = { occupiedPitchIds };
