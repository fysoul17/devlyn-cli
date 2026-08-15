"use strict";

function closeServiceVisit(log, odometer) {
  return log.recordService({ odometer, station: "west-bay" });
}

module.exports = { closeServiceVisit };
