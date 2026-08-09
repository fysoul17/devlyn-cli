import assert from "node:assert/strict";
import test from "node:test";

import { MigrationJournal } from "../journal.js";

test("claims and commits a key once", () => {
  const journal = new MigrationJournal();
  assert.equal(journal.claim("m-1"), true);
  journal.commit("m-1", 1);
  assert.equal(journal.claim("m-1"), false);
  assert.deepEqual(journal.entries(), [{ key: "m-1", revision: 1 }]);
});
