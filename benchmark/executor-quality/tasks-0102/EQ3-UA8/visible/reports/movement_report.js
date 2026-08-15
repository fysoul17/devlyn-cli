"use strict";

function movementsFor(yard, containerId) {
  return yard.journal.filter((entry) => entry.containerId === containerId);
}

module.exports = { movementsFor };
