import assert from "node:assert/strict";
import test from "node:test";

import { SchemaCheck, SchemaDiagnosticJournal } from "../schema-check.js";
import { PublishTokenGate } from "../token-gate.js";

test("publish tokens are active and namespace scoped", () => {
  const gate = new PublishTokenGate([
    { id: "active", actorId: "builder", active: true, namespaces: ["stable"] },
    { id: "expired", actorId: "builder", active: false, namespaces: ["stable"] },
  ]);
  assert.deepEqual(gate.authorize("active", "stable"), { ok: true, actorId: "builder" });
  assert.deepEqual(gate.authorize("expired", "stable"), { ok: false, error: "publish_denied" });
  assert.deepEqual(gate.authorize("active", "preview"), { ok: false, error: "publish_denied" });
});

test("schema diagnostics preserve declaration order within one reason", () => {
  const journal = new SchemaDiagnosticJournal();
  const checker = new SchemaCheck(journal);
  const issue = checker.inspect("stable", "4.0.0", {
    schemaVersion: 2,
    attributes: [
      { field: "digest", value: 17 },
      { field: "name", value: false },
      { field: "mediaType", value: "application/example" },
    ],
  });
  assert.equal(issue.reason, "wrong_type");
  assert.equal(issue.field, "digest");
  assert.equal(journal.entries.length, 1);
});
