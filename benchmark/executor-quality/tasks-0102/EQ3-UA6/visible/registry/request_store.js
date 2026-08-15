"use strict";

function requestById(state, id) {
  return state.requests.find((request) => request.id === id) || null;
}

module.exports = { requestById };
