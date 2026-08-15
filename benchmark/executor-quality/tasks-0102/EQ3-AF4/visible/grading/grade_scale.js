"use strict";

function gradeBand(weight) {
  if (weight >= 20) return "premium";
  if (weight >= 12) return "standard";
  return "utility";
}

module.exports = { gradeBand };
