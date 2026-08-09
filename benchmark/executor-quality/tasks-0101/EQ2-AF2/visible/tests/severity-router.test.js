"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { SeverityRouter } = require("../severity-router");

test("places a single ticket in the first slot", () => {
  const router = new SeverityRouter();
  const result = router.place([{ id: "T1", severity: "low", arrival: 0 }]);

  assert.equal(result[0].slot, 1);
});
