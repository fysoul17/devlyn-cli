"use strict";

function openAssignment(harbor, request) {
  const pilot = harbor.pilots.find((item) => item.id === request.pilotId);
  const berth = harbor.berths.find((item) => item.id === request.berthId);
  if (!pilot || !berth || pilot.status !== "ready" || berth.status !== "open") {
    return { opened: false, assignmentId: request.assignmentId };
  }
  pilot.status = "assigned";
  pilot.assignmentId = request.assignmentId;
  berth.status = "occupied";
  berth.assignmentId = request.assignmentId;
  harbor.assignments.push({ id: request.assignmentId, ...request, status: "active" });
  return { opened: true, assignmentId: request.assignmentId };
}

function closeAssignment(harbor, assignmentId, closedAt) {
  return { closed: false, assignmentId, closedAt };
}

function activeAssignments(harbor) {
  return harbor.assignments.filter((item) => item.status === "active");
}

module.exports = { activeAssignments, closeAssignment, openAssignment };
