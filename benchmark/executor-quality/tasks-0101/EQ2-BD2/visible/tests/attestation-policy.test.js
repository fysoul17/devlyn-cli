"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { AttestationPolicy } = require("../attestation-policy");

test("trust is scoped to the requested rollout ring", () => {
  const policy = new AttestationPolicy({ canary: ["release"], stable: ["ops"] });

  assert.equal(policy.allows({ ring: "canary", signer: "release" }), true);
  assert.equal(policy.allows({ ring: "stable", signer: "release" }), false);
});
