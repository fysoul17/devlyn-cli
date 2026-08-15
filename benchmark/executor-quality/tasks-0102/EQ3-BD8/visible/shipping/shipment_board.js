"use strict";

function distributeLot(warehouse, lotId, shipmentId, units) {
  const lot = warehouse.lots.find((item) => item.id === lotId);
  if (!lot || lot.status === "quarantined" || units <= 0) return false;
  warehouse.distributions.push({ lotId, shipmentId, units });
  return true;
}

module.exports = { distributeLot };
