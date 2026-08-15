"use strict";

function assignmentSummary(assignment) {
  return {
    orderId: assignment.orderId,
    courierId: assignment.courierId,
    status: assignment.status,
  };
}

function listAssignments(state) {
  return [...state.assignments.values()].map(assignmentSummary);
}

module.exports = { assignmentSummary, listAssignments };
