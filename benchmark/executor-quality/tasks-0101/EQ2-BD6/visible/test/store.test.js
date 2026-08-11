import assert from "node:assert/strict";
import test from "node:test";

import { InventoryStore } from "../inventory_store.js";

test("snapshot restoration preserves canonical bytes", () => {
  const store = new InventoryStore({ B: 4, A: 7 });
  const before = store.snapshotBytes();
  store.take({ quantity: 2, sku: "A" });
  store.restoreBytes(before);
  assert.deepEqual(store.snapshotBytes(), before);
});

test("locked bins and insufficient stock have distinct causes", () => {
  const store = new InventoryStore({ A: 7, B: 2 }, { locked: ["A"] });
  assert.equal(store.problemFor({ quantity: 1, sku: "A" }), "conflict");
  assert.equal(store.problemFor({ quantity: 3, sku: "B" }), "shortage");
  assert.equal(store.problemFor({ quantity: 2, sku: "B" }), null);
});
