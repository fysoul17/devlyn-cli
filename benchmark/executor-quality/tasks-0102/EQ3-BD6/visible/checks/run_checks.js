"use strict";

const assert = require("node:assert/strict");
const { makeFestival } = require("../support/fixtures");
const { revokePermit } = require("../issuer/permit_issuer");
const { activePermitIds } = require("../issuer/permit_registry");

const festival = makeFestival();
const result = revokePermit(festival, "F-41", 5);
assert.equal(result.revoked, true);
assert.equal(activePermitIds(festival).includes("F-41"), false);
console.log("issuer checks passed");
