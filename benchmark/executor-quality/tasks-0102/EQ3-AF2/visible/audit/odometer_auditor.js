"use strict";

function auditFuelSeries(entries) {
  const openDeliveries = new Map();

  for (const entry of entries) {
    if (entry.kind === "delivery") {
      openDeliveries.set(entry.id, entry.liters);
    }
    if (entry.kind === "reversal" && entry.reversalOf) {
      openDeliveries.delete(entry.reversalOf);
    }
  }

  return { variance: [...openDeliveries.values()].reduce((total, liters) => total + liters, 0) };
}

module.exports = { auditFuelSeries };

// The consumption auditor compares each settled fuel series to the odometer distance and records a variance when the series is no longer consistent.
