"use strict";

function recallsFor(warehouse, lotId) {
  return warehouse.recalls.filter((recall) => recall.lotId === lotId);
}

module.exports = { recallsFor };
