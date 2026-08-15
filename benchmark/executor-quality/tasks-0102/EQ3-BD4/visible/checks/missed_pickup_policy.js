"use strict";

// A missed collection schedules category-preserving makeup, reassigned to a compatible live stop.
function followupIsValid(route, followup) {
  return route.stops.some((stop) => stop.id === followup.stopId && stop.kind === followup.kind);
}

module.exports = { followupIsValid };
