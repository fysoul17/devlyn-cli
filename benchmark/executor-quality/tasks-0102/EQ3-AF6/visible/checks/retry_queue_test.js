"use strict";

const assert = require("node:assert/strict");
const { makeProductionDay } = require("../support/fixtures");
const { failRise } = require("../planner/batch_planner");

const day = makeProductionDay();
const result = failRise(day, "B17");
assert.equal(result.requeued, true);
assert.deepEqual(day.retryQueue, ["B17"]);
