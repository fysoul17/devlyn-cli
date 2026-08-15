"use strict";

function portionsFor(warehouse, lotId) {
  return warehouse.distributions.filter((portion) => portion.lotId === lotId);
}

module.exports = { portionsFor };
