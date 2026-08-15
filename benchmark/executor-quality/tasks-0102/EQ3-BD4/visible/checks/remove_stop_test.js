"use strict";

const { boardStops } = require("../route/route_board");

function removalShown(route, stopId) {
  return !boardStops(route).includes(stopId);
}

function boardCountIs(route, count) {
  return boardStops(route).length === count;
}

module.exports = { removalShown, boardCountIs };
