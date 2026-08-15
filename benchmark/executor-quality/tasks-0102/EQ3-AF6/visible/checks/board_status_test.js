"use strict";

const assert = require("node:assert/strict");
const { makeProductionDay } = require("../support/fixtures");
const { failRise } = require("../planner/batch_planner");
const { boardStatus } = require("../planner/production_board");

const day = makeProductionDay();
failRise(day, "B17");
assert.deepEqual(boardStatus(day, "B17"), { state: "queued", rise: "failed" });
