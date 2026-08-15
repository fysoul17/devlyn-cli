"use strict";

function currentAssignmentIds(harbor) {
  return harbor.assignments.filter((item) => item.status === "active").map((item) => item.id);
}

module.exports = { currentAssignmentIds };
