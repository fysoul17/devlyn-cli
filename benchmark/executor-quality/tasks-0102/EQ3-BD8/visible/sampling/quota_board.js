"use strict";

function usedSlots(warehouse, classCode) {
  const limit = warehouse.classLimits.find((item) => item.classCode === classCode);
  return limit ? limit.used : null;
}

module.exports = { usedSlots };
