import assert from "node:assert/strict";
import test from "node:test";

import { SchemaState } from "../schema-state.js";
import { applyMigrationStep } from "../step-applier.js";

test("applies one schema change", () => {
  const state = new SchemaState({ users: { columns: ["id"], indexes: [] } });
  applyMigrationStep(state, {
    key: "add-email",
    change: { kind: "column", table: "users", name: "email" },
    failAfterApply: false,
  });
  assert.deepEqual(state.view(), {
    schema: { users: { columns: ["id", "email"], indexes: [] } },
    revision: 1,
  });
});
