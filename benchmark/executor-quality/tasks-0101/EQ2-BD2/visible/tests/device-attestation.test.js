"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { attestRollout } = require("../device-attestation");

test("attests one trusted firmware request into the first wave", () => {
  const result = attestRollout(
    [{ id: "d1", signer: "release", ring: "canary", priority: 4 }],
    { canary: ["release"] },
  );

  assert.deepEqual(result, {
    accepted: [{ id: "d1", wave: 1, slot: 1 }],
    rejected: [],
  });
});
