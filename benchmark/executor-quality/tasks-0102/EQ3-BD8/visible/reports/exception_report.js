"use strict";

function failureTotal(warehouse) {
  return warehouse.recalls.length;
}

module.exports = { failureTotal };
