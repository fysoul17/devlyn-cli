import assert from "node:assert/strict";
import test from "node:test";

import { DeliveryDedup } from "../delivery-dedup.js";

test("records each notification recipient once", () => {
  const dedup = new DeliveryDedup();
  assert.equal(dedup.record("n1", "ann"), true);
  assert.equal(dedup.record("n1", "ann"), false);
  assert.equal(dedup.record("n1", "bo"), true);
  assert.equal(dedup.record("n2", "ann"), true);
});
