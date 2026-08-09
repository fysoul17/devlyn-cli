"use strict";

function rankRequests(requests) {
  return [...requests].sort(
    (left, right) => right.priority - left.priority || left.arrival - right.arrival,
  );
}

module.exports = { rankRequests };
