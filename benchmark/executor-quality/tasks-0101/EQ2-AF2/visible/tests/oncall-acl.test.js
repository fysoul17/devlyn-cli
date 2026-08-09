"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { OnCallAcl } = require("../oncall-acl");

test("permits only the assigned requester for a service", () => {
  const acl = new OnCallAcl({ api: ["ada"] });

  assert.equal(acl.allows({ requester: "ada", service: "api" }), true);
  assert.equal(acl.allows({ requester: "bea", service: "api" }), false);
});
