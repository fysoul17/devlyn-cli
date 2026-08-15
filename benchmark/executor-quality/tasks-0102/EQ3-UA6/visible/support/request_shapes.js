"use strict";

function isCorrection(value) {
  return Boolean(value && value.id && value.replaces && value.desiredCarrier);
}

module.exports = { isCorrection };
