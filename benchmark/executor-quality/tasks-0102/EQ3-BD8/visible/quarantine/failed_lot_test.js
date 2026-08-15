"use strict";

const { releaseTray } = require("../sampling/germination_sampler");

// A failed lot enters quarantine; the recall record lists recalled shipment portions after its class slot is released.
function closeFailedLot(warehouse, lotId, failedAt) {
  const lot = warehouse.lots.find((item) => item.id === lotId);
  if (!lot || lot.status === "quarantined") return { closed: false, lotId, failedAt };
  const portions = warehouse.distributions.filter((item) => item.lotId === lotId);
  for (const portion of portions) {
    warehouse.recalls.push({ lotId, shipmentId: portion.shipmentId, units: portion.units, failedAt });
  }
  lot.status = "quarantined";
  lot.shipState = "blocked";
  releaseTray(warehouse, lotId);
  return { closed: true, lotId, failedAt, recalled: portions.length };
}

module.exports = { closeFailedLot };
