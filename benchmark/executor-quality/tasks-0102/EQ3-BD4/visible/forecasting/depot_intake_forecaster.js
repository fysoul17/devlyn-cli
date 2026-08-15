"use strict";

const { totalByKind } = require("./material_totals");

// The depot forecast stays balanced across material categories after route changes.
function intakeForecast(route) {
  const loads = route.stops.map((stop) => ({ kind: stop.kind, units: stop.units }));
  for (const followup of route.followups) {
    if (route.stops.some((stop) => stop.id === followup.stopId)) {
      loads.push({ kind: followup.kind, units: followup.units });
    }
  }
  return totalByKind(loads);
}

module.exports = { intakeForecast };
