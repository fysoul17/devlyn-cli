"use strict";

function readyPilotIds(harbor) {
  return harbor.pilots.filter((item) => item.status === "ready").map((item) => item.id);
}

module.exports = { readyPilotIds };
