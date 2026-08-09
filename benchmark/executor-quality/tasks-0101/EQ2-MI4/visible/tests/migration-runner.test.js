import assert from "node:assert/strict";
import test from "node:test";

import { MigrationJournal } from "../journal.js";
import { runMigrationBatch } from "../migration-runner.js";
import { SchemaState } from "../schema-state.js";

test("applies a successful migration only once", () => {
  const state = new SchemaState({ users: { columns: ["id"], indexes: [] } });
  const journal = new MigrationJournal();
  const batch = [{
    key: "add-email",
    change: { kind: "column", table: "users", name: "email" },
    failAfterApply: false,
  }];

  assert.equal(runMigrationBatch(state, journal, batch).ok, true);
  assert.deepEqual(runMigrationBatch(state, journal, batch).skipped, ["add-email"]);
  assert.deepEqual(journal.entries(), [{ key: "add-email", revision: 1 }]);
});
