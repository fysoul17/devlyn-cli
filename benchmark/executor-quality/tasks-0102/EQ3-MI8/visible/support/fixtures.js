"use strict";

const { harborState } = require("../registry/harbor_state");

function harborForDesk(assignmentId, pilotId, berthId) {
  const harbor = harborState(
    [{ id: pilotId, status: "ready", assignmentId: null }],
    [{ id: berthId, status: "open", assignmentId: null }],
  );
  harbor.request = { assignmentId, pilotId, berthId, plannedFor: 19 };
  return harbor;
}

function harborForScenarios(data) {
  return harborState(
    data.pilots.map((item) => ({ ...item })),
    data.berths.map((item) => ({ ...item })),
  );
}

module.exports = { harborForDesk, harborForScenarios };
