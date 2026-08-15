"use strict";

function mappingFor(state, number) {
  return state.numberMap[number] || null;
}

module.exports = { mappingFor };
