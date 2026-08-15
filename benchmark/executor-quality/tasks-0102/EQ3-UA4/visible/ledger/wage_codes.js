"use strict";

const supportedCodes = ["REG", "OT", "LEAVE"];

function isSupported(code) {
  return supportedCodes.includes(code);
}

module.exports = { isSupported, supportedCodes };
