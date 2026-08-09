#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys


workdir = pathlib.Path(sys.argv[1])
runner = r'''import { pathToFileURL } from "node:url";
const root = pathToFileURL(`${process.argv[1]}/`);
const { MigrationJournal } = await import(new URL("journal.js", root));
const { runMigrationBatch } = await import(new URL("migration-runner.js", root));
const { SchemaState } = await import(new URL("schema-state.js", root));

const same = (left, right) => JSON.stringify(left) === JSON.stringify(right);
const emptySchema = () => ({ users: { columns: ["id"], indexes: [] } });
const step = (key, kind, name, failAfterApply = false) => ({
  key,
  change: { kind, table: "users", name },
  failAfterApply,
});

function rollbackFromEmptyJournal() {
  const state = new SchemaState(emptySchema());
  const journal = new MigrationJournal();
  const before = state.view();
  const outcome = runMigrationBatch(state, journal, [
    step("r-a", "column", "email"),
    step("r-b", "index", "users_email", true),
  ]);
  return !outcome.ok && same(state.view(), before) && same(journal.entries(), []);
}

function rollbackOverExistingHistory() {
  const schema = { users: { columns: ["id", "email"], indexes: [] } };
  const state = new SchemaState(schema, 1);
  const prior = [{ key: "prior", revision: 1 }];
  const journal = new MigrationJournal(prior);
  const before = state.view();
  const outcome = runMigrationBatch(state, journal, [
    step("r-c", "index", "users_email"),
    step("r-d", "column", "phone", true),
  ]);
  return !outcome.ok && same(state.view(), before) && same(journal.entries(), prior);
}

function replaySuccessfulBatch() {
  const state = new SchemaState(emptySchema());
  const journal = new MigrationJournal();
  const batch = [
    step("i-a", "column", "email"),
    step("i-b", "index", "users_email"),
  ];
  const first = runMigrationBatch(state, journal, batch);
  const afterFirst = state.view();
  const second = runMigrationBatch(state, journal, batch);
  return first.ok
    && second.ok
    && same(second.applied, [])
    && same(second.skipped, ["i-a", "i-b"])
    && same(state.view(), afterFirst)
    && same(journal.entries(), [
      { key: "i-a", revision: 1 },
      { key: "i-b", revision: 2 },
    ]);
}

function duplicateInsideBatch() {
  const state = new SchemaState(emptySchema());
  const journal = new MigrationJournal();
  const duplicate = step("i-c", "column", "locale");
  const outcome = runMigrationBatch(state, journal, [duplicate, duplicate]);
  return outcome.ok
    && same(outcome.applied, ["i-c"])
    && same(outcome.skipped, ["i-c"])
    && same(state.view(), {
      schema: { users: { columns: ["id", "locale"], indexes: [] } },
      revision: 1,
    })
    && same(journal.entries(), [{ key: "i-c", revision: 1 }]);
}

function failedAttemptThenReplay() {
  const state = new SchemaState(emptySchema());
  const journal = new MigrationJournal();
  const before = state.view();
  const batch = [
    step("x-a", "column", "email"),
    step("x-b", "index", "users_email", true),
    step("x-c", "column", "phone"),
  ];
  const first = runMigrationBatch(state, journal, batch);
  const rolledBack = same(state.view(), before) && same(journal.entries(), []);
  batch[1].failAfterApply = false;
  const replay = runMigrationBatch(state, journal, batch);
  return !first.ok
    && rolledBack
    && replay.ok
    && same(replay.applied, ["x-a", "x-b", "x-c"])
    && same(replay.skipped, [])
    && same(state.view(), {
      schema: {
        users: {
          columns: ["id", "email", "phone"],
          indexes: ["users_email"],
        },
      },
      revision: 3,
    })
    && same(journal.entries(), [
      { key: "x-a", revision: 1 },
      { key: "x-b", revision: 2 },
      { key: "x-c", revision: 3 },
    ]);
}

process.stdout.write(JSON.stringify([
  rollbackFromEmptyJournal(),
  rollbackOverExistingHistory(),
  replaySuccessfulBatch(),
  duplicateInsideBatch(),
  failedAttemptThenReplay(),
]));
'''
invariant = "Migration batches restore the schema and durable journal to their exact pre-batch states when any step fails, migration keys apply at most once on successful runs, and replaying a batch whose first partially applied attempt rolled back starts from that clean state so every step is applied and journaled exactly once."

completed = subprocess.run(
    [
        "node",
        "--input-type=module",
        "--eval",
        runner,
        str(workdir),
    ],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
    timeout=10,
)
if completed.returncode != 0:
    raise SystemExit(completed.stderr)

passed = json.loads(completed.stdout)
ids = ["axis1-a", "axis1-b", "axis2-a", "axis2-b", "interaction"]
print(json.dumps({"manifestations": [
    {"id": identifier, "invariant": invariant, "passed": result}
    for identifier, result in zip(ids, passed, strict=True)
]}))
