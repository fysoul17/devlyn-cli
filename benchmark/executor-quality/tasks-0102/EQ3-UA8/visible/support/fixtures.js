"use strict";

const { makeYard } = require("../yard/yard_state");

function rejectedYard() {
  return makeYard({ rejectedIds: ["CTR-19"], secondRejectedIds: ["CTR-17"] });
}

module.exports = { rejectedYard };
