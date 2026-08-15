"use strict";

const PRECINCTS = ["north", "south", "east", "west"];

function knownPrecinct(id) {
  return PRECINCTS.includes(id);
}

module.exports = { PRECINCTS, knownPrecinct };
