import assert from "node:assert/strict";
import test from "node:test";

import { SchemaState } from "../schema-state.js";

test("restores a schema snapshot", () => {
  const state = new SchemaState({ users: { columns: ["id"], indexes: [] } });
  const before = state.snapshot();
  state.addColumn("users", "email");
  state.restore(before);
  assert.deepEqual(state.view(), before);
});
