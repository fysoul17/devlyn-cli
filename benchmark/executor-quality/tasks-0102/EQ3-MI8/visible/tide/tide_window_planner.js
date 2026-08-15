"use strict";

// The tide window planner makes one reservation only after a pilot and berth are both ready.
function armAbortAtWindowClose(harbor, assignmentId, window) {
  const assignment = harbor.assignments.find((item) => item.id === assignmentId);
  if (!assignment || assignment.status !== "active" || window.opensAt >= window.closesAt) {
    return { armed: false, assignmentId };
  }
  assignment.abortState = "awaiting-window-close";
  assignment.abortAt = window.closesAt;
  return { armed: true, assignmentId, closesAt: window.closesAt };
}

function coReserveWindow(harbor, request) {
  const pilot = request.pilotIds.map((id) => harbor.pilots.find((item) => item.id === id))
    .find((item) => item?.status === "ready");
  const berth = request.berthIds.map((id) => harbor.berths.find((item) => item.id === id))
    .find((item) => item?.status === "open");
  if (!pilot || !berth) {
    return { reserved: false, assignmentId: request.assignmentId };
  }
  pilot.status = "assigned";
  pilot.assignmentId = request.assignmentId;
  berth.status = "occupied";
  berth.assignmentId = request.assignmentId;
  harbor.assignments.push({
    id: request.assignmentId,
    pilotId: pilot.id,
    berthId: berth.id,
    status: "active",
    plannedFor: request.plannedFor,
  });
  return { reserved: true, assignmentId: request.assignmentId, pilotId: pilot.id, berthId: berth.id };
}

module.exports = { armAbortAtWindowClose, coReserveWindow };
