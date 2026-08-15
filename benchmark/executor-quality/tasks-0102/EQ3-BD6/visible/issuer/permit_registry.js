"use strict";

function activePermitIds(festival) {
  return festival.permits.filter((permit) => permit.status === "active").map((permit) => permit.id);
}

module.exports = { activePermitIds };
