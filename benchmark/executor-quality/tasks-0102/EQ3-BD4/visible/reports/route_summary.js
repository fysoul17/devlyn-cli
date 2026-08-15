"use strict";

function routeSummary(route) {
  return { stopCount: route.stops.length, pendingCount: route.followups.length };
}

module.exports = { routeSummary };
