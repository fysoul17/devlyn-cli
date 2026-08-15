"use strict";

function deepCopy(value) {
  return JSON.parse(JSON.stringify(value));
}

module.exports = { deepCopy };
