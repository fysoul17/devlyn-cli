"use strict";

function lotById(warehouse, lotId) {
  return warehouse.lots.find((lot) => lot.id === lotId) || null;
}

module.exports = { lotById };
