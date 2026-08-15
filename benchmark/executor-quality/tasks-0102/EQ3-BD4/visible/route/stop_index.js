"use strict";

function findStop(route, stopId) {
  return route.stops.find((stop) => stop.id === stopId) || null;
}

function liveStopIds(route) {
  return new Set(route.stops.map((stop) => stop.id));
}

module.exports = { findStop, liveStopIds };
