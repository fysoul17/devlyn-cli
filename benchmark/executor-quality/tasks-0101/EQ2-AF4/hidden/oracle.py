#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys


workdir = pathlib.Path(sys.argv[1])
runner = r'''import { pathToFileURL } from "node:url";
const root = pathToFileURL(`${process.argv[1]}/`);
const { CacheStore } = await import(new URL("cache-store.js", root));
const { GenerationCounter } = await import(new URL("generation-counter.js", root));
const { runPurgeBatch } = await import(new URL("purge-batch.js", root));
const { PurgeCommand } = await import(new URL("purge-command.js", root));

const same = (left, right) => JSON.stringify(left) === JSON.stringify(right);
const entry = (key, scope, generation) => ({ key, scope, generation });

function rollbackFreshCounters() {
  const store = new CacheStore([
    entry("api-stale", "api", 0),
    entry("api-current", "api", 2),
  ]);
  const counter = new GenerationCounter();
  const beforeStore = store.view();
  const beforeCounter = counter.view();
  const outcome = runPurgeBatch(
    store,
    counter,
    "failing-fresh",
    [new PurgeCommand("api", { failAfterPurge: true })],
  );
  return !outcome.ok
    && same(store.view(), beforeStore)
    && same(counter.view(), beforeCounter);
}

function rollbackWithPriorState() {
  const store = new CacheStore([
    entry("api-v1", "api", 1),
    entry("media-v3", "media", 3),
  ]);
  const counter = new GenerationCounter({ api: 1, media: 3 }, ["earlier"]);
  const beforeStore = store.view();
  const beforeCounter = counter.view();
  const outcome = runPurgeBatch(
    store,
    counter,
    "failing-history",
    [new PurgeCommand("api", { failAfterPurge: true })],
  );
  return !outcome.ok
    && same(store.view(), beforeStore)
    && same(counter.view(), beforeCounter);
}

function successfulReplayIsSkipped() {
  const store = new CacheStore([
    entry("api-v0", "api", 0),
    entry("api-v2", "api", 2),
  ]);
  const counter = new GenerationCounter();
  const commands = [new PurgeCommand("api")];
  const first = runPurgeBatch(store, counter, "stable-replay", commands);
  const afterStore = store.view();
  const afterCounter = counter.view();
  const second = runPurgeBatch(store, counter, "stable-replay", commands);
  return first.ok
    && !first.skipped
    && second.ok
    && second.skipped
    && same(second.purged, [])
    && same(store.view(), afterStore)
    && same(counter.view(), afterCounter);
}

function duplicateIdSkipsNewCommands() {
  const store = new CacheStore([
    entry("api-v0", "api", 0),
    entry("media-v0", "media", 0),
  ]);
  const counter = new GenerationCounter();
  const first = runPurgeBatch(
    store,
    counter,
    "duplicate-id",
    [new PurgeCommand("api")],
  );
  const second = runPurgeBatch(
    store,
    counter,
    "duplicate-id",
    [new PurgeCommand("media")],
  );
  return first.ok
    && second.ok
    && second.skipped
    && same(store.view(), [entry("media-v0", "media", 0)])
    && same(counter.view(), {
      generations: { api: 1 },
      completed: ["duplicate-id"],
    });
}

function failedBatchThenSameCommandReplay() {
  const store = new CacheStore([
    entry("api-stale", "api", 0),
    entry("api-current", "api", 4),
    entry("media-stale", "media", 0),
  ]);
  const counter = new GenerationCounter();
  const commands = [
    new PurgeCommand("api"),
    new PurgeCommand("media", { failAfterPurge: true }),
  ];
  const beforeStore = store.view();
  const beforeCounter = counter.view();
  const first = runPurgeBatch(store, counter, "recoverable", commands);
  const rolledBack = same(store.view(), beforeStore)
    && same(counter.view(), beforeCounter);
  commands[1].failAfterPurge = false;
  const replay = runPurgeBatch(store, counter, "recoverable", commands);
  return !first.ok
    && rolledBack
    && replay.ok
    && !replay.skipped
    && same(replay.purged, ["api-stale", "media-stale"])
    && same(store.view(), [entry("api-current", "api", 4)])
    && same(counter.view(), {
      generations: { api: 1, media: 1 },
      completed: ["recoverable"],
    });
}

process.stdout.write(JSON.stringify([
  rollbackFreshCounters(),
  rollbackWithPriorState(),
  successfulReplayIsSkipped(),
  duplicateIdSkipsNewCommands(),
  failedBatchThenSameCommandReplay(),
]));
'''
invariant = "Failed purge batches restore cached entries and generation counters to their exact pre-batch states, successful batch identifiers take effect at most once, and replaying the same commands after a partially executed batch rolls back recomputes generations from that clean state so every requested scope is purged exactly once."

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
