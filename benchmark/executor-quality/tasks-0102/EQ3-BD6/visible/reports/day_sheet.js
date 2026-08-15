"use strict";

function daySheet(festival) {
  return { active: festival.permits.filter((permit) => permit.status === "active").length };
}

module.exports = { daySheet };
