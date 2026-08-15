"use strict";

function copy(value) {
  return JSON.parse(JSON.stringify(value));
}

module.exports = { copy };
