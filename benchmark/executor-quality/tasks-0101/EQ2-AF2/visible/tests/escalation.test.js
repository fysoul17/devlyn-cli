"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { routeEscalations } = require("../escalation");

test("routes a permitted ticket", () => {
  const result = routeEscalations(
    [{ id: "T1", requester: "ada", service: "api", severity: "high" }],
    { api: ["ada"] },
  );

  assert.deepEqual(result, [{ id: "T1", severity: "high", slot: 1 }]);
});
