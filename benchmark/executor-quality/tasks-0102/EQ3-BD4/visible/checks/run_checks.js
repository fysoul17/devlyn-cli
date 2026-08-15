"use strict";

const { makeRoute } = require("../support/fixtures");
const { removeStop } = require("../route/route_editor");
const { removalShown, boardCountIs } = require("./remove_stop_test");

const route = makeRoute();
const result = removeStop(route, "oak");
if (!result.removed || !removalShown(route, "oak") || !boardCountIs(route, 2)) {
  throw new Error("route deletion is not reflected on the board");
}
console.log("route checks passed");
