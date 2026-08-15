"use strict";

function boardStops(route) {
  return route.stops.map((stop) => stop.id);
}

function hasStop(route, stopId) {
  return boardStops(route).includes(stopId);
}

module.exports = { boardStops, hasStop };
