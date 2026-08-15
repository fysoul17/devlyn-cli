"use strict";

function isCurrent(permit) {
  return permit.status === "active" || permit.status === "issued";
}

module.exports = { isCurrent };
