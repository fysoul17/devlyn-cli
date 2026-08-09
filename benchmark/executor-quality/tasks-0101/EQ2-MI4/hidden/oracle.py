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
const baseSchema = () => ({
  users: { columns: ["id"], indexes: [] },
  teams: { columns: ["id"], indexes: [] },
});
const step = (key, kind, name, failAfterApply = false, table = "users") => ({
  key,
  change: { kind, table, name },
  failAfterApply,
});

function rollbackAfterDispatchFailure() {
  const state = new SchemaState(baseSchema(), 4);
  const journal = new MigrationJournal();
  const before = state.view();
  const journalBefore = journal.snapshot();
  const outcome = runMigrationBatch(state, journal, [
    step("r-a", "column", "slug", false, "teams"),
    step("r-b", "trigger", "users_audit"),
  ]);
  return !outcome.ok
    && same(state.view(), before)
    && same(journal.snapshot(), journalBefore);
}

function rollbackPreservesClaimsAndHistory() {
  const schema = baseSchema();
  schema.users.columns.push("email");
  schema.teams.indexes.push("teams_slug");
  const state = new SchemaState(schema, 6);
  const prior = [
    { key: "prior-users", revision: 2 },
    { key: "prior-teams", revision: 6 },
  ];
  const journal = new MigrationJournal(prior);
  journal.claim("reserved-next");
  const before = state.view();
  const journalBefore = journal.snapshot();
  const outcome = runMigrationBatch(state, journal, [
    step("r-c", "index", "users_email"),
    step("r-d", "column", "timezone", true, "teams"),
  ]);
  return !outcome.ok
    && same(state.view(), before)
    && same(journal.snapshot(), journalBefore)
    && journal.claim("r-c")
    && !journal.claim("reserved-next");
}

function interleavedCommittedKeysAreSkipped() {
  const schema = baseSchema();
  schema.users.columns.push("email");
  const state = new SchemaState(schema, 1);
  const journal = new MigrationJournal([{ key: "i-old", revision: 1 }]);
  const batch = [
    step("i-old", "column", "ignored"),
    step("i-new", "index", "users_email"),
    step("i-old", "column", "still-ignored"),
  ];
  const outcome = runMigrationBatch(state, journal, batch);
  return outcome.ok
    && same(outcome.applied, ["i-new"])
    && same(outcome.skipped, ["i-old", "i-old"])
    && same(state.view(), {
      schema: {
        users: { columns: ["id", "email"], indexes: ["users_email"] },
        teams: { columns: ["id"], indexes: [] },
      },
      revision: 2,
    })
    && same(journal.entries(), [
      { key: "i-old", revision: 1 },
      { key: "i-new", revision: 2 },
    ]);
}

function separatedDuplicateAppliesOnce() {
  const state = new SchemaState(baseSchema());
  const journal = new MigrationJournal();
  const duplicate = step("i-repeat", "column", "locale");
  const outcome = runMigrationBatch(state, journal, [
    duplicate,
    step("i-between", "column", "slug", false, "teams"),
    duplicate,
  ]);
  return outcome.ok
    && same(outcome.applied, ["i-repeat", "i-between"])
    && same(outcome.skipped, ["i-repeat"])
    && same(state.view(), {
      schema: {
        users: { columns: ["id", "locale"], indexes: [] },
        teams: { columns: ["id", "slug"], indexes: [] },
      },
      revision: 2,
    })
    && same(journal.entries(), [
      { key: "i-repeat", revision: 1 },
      { key: "i-between", revision: 2 },
    ]);
}

function correctedDispatchIsRetriedFromSnapshot() {
  const schema = baseSchema();
  schema.users.columns.push("email");
  const state = new SchemaState(schema, 3);
  const prior = [{ key: "x-prior", revision: 3 }];
  const journal = new MigrationJournal(prior);
  const before = state.view();
  const journalBefore = journal.snapshot();
  const batch = [
    step("x-team", "column", "slug", false, "teams"),
    step("x-phone", "column", "phone"),
    step("x-dispatch", "constraint", "users_email_unique"),
  ];
  const first = runMigrationBatch(state, journal, batch);
  const rolledBack = same(state.view(), before) && same(journal.snapshot(), journalBefore);
  batch[2].change.kind = "index";
  const replay = runMigrationBatch(state, journal, batch);
  return !first.ok
    && rolledBack
    && replay.ok
    && same(replay.applied, ["x-team", "x-phone", "x-dispatch"])
    && same(replay.skipped, [])
    && same(state.view(), {
      schema: {
        users: { columns: ["id", "email", "phone"], indexes: ["users_email_unique"] },
        teams: { columns: ["id", "slug"], indexes: [] },
      },
      revision: 6,
    })
    && same(journal.entries(), [
      { key: "x-prior", revision: 3 },
      { key: "x-team", revision: 4 },
      { key: "x-phone", revision: 5 },
      { key: "x-dispatch", revision: 6 },
    ]);
}

process.stdout.write(JSON.stringify([
  rollbackAfterDispatchFailure(),
  rollbackPreservesClaimsAndHistory(),
  interleavedCommittedKeysAreSkipped(),
  separatedDuplicateAppliesOnce(),
  correctedDispatchIsRetriedFromSnapshot(),
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
