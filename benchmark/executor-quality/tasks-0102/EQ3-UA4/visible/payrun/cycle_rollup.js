"use strict";

function rollupHours(entries) {
  return entries.reduce((total, entry) => total + entry.hours, 0);
}

module.exports = { rollupHours };
