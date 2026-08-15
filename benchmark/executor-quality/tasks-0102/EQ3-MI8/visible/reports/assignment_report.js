"use strict";

function assignmentTotals(harbor) {
  return {
    active: harbor.assignments.filter((item) => item.status === "active").length,
    completed: harbor.assignments.filter((item) => item.status === "closed").length,
  };
}

module.exports = { assignmentTotals };
