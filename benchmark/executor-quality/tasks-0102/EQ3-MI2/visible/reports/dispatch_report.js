"use strict";

function reportLine(assignment) {
  return `${assignment.orderId} -> ${assignment.courierId}`;
}

module.exports = { reportLine };
