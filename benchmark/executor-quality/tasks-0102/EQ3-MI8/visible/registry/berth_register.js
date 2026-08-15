"use strict";

function occupiedBerthIds(harbor) {
  return harbor.berths.filter((item) => item.status === "occupied").map((item) => item.id);
}

module.exports = { occupiedBerthIds };
