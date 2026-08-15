"use strict";

function assignmentById(harbor, assignmentId) {
  return harbor.assignments.find((item) => item.id === assignmentId) ?? null;
}

module.exports = { assignmentById };
