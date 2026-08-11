import assert from "node:assert/strict";
import test from "node:test";

import { CommitFault, WriteFault } from "../errors.js";
import { InventoryStore } from "../inventory_store.js";
import { executePickWave } from "../pick_executor.js";

test("a successful wave records its picks and commit", () => {
  const store = new InventoryStore({ A: 8, B: 5 });
  const result = executePickWave(store, "wave-ok", [
    { quantity: 3, sku: "A" },
    { quantity: 2, sku: "B" },
  ]);

  assert.deepEqual(result.picks, [
    { quantity: 3, sku: "A" },
    { quantity: 2, sku: "B" },
  ]);
  assert.deepEqual(store.view().completedWaves, ["wave-ok"]);
});

test("a physical write fault restores the wave start", () => {
  const store = new InventoryStore({ A: 8 });
  const before = store.snapshotBytes();

  assert.throws(
    () => executePickWave(store, "wave-write", [{ failAfterWrite: true, quantity: 3, sku: "A" }]),
    WriteFault,
  );
  assert.deepEqual(store.snapshotBytes(), before);
});

test("a commit fault restores multiple completed picks", () => {
  const store = new InventoryStore({ A: 8, B: 5 });
  const before = store.snapshotBytes();

  assert.throws(
    () => executePickWave(
      store,
      "wave-commit",
      [{ quantity: 3, sku: "A" }, { quantity: 2, sku: "B" }],
      { failCommit: true },
    ),
    CommitFault,
  );
  assert.deepEqual(store.snapshotBytes(), before);
});
