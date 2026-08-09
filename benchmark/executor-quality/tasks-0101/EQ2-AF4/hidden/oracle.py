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

function rollbackAfterSeveralPurges() {
  const store = new CacheStore([
    entry("api-v0", "api", 0),
    entry("api-v2", "api", 2),
    entry("media-v0", "media", 0),
    entry("media-v3", "media", 3),
  ]);
  const counter = new GenerationCounter();
  const beforeStore = store.view();
  const beforeCounter = counter.view();
  const outcome = runPurgeBatch(
    store,
    counter,
    "late-failure",
    [
      new PurgeCommand("api"),
      new PurgeCommand("media", { failAfterPurge: true }),
    ],
  );
  return !outcome.ok
    && same(outcome.purged, ["api-v0"])
    && same(store.view(), beforeStore)
    && same(counter.view(), beforeCounter);
}

function rollbackKeepsPreparedBaseline() {
  const store = new CacheStore([
    entry("api-v4", "api", 4),
    entry("api-v7", "api", 7),
    entry("media-v2", "media", 2),
  ]);
  const counter = new GenerationCounter({ api: 4, media: 2 }, ["earlier-a", "earlier-b"]);
  const prepared = new PurgeCommand("api");
  prepared.prepare(counter);
  const beforeStore = store.view();
  const beforeCounter = counter.view();
  const outcome = runPurgeBatch(
    store,
    counter,
    "prepared-history",
    [prepared, new PurgeCommand("media", { failAfterPurge: true })],
  );
  return !outcome.ok
    && same(store.view(), beforeStore)
    && same(counter.view(), beforeCounter)
    && prepared.preparation() === 5;
}

function precompletedBatchNeverPreparesCommands() {
  const store = new CacheStore([
    entry("api-v0", "api", 0),
    entry("media-v0", "media", 0),
  ]);
  const counter = new GenerationCounter({ api: 8 }, ["already-done"]);
  const commands = [
    new PurgeCommand("api", { failAfterPurge: true }),
    new PurgeCommand("media"),
  ];
  const beforeStore = store.view();
  const beforeCounter = counter.view();
  const outcome = runPurgeBatch(store, counter, "already-done", commands);
  return outcome.ok
    && outcome.skipped
    && same(outcome.purged, [])
    && same(commands.map((command) => command.preparation()), [null, null])
    && same(store.view(), beforeStore)
    && same(counter.view(), beforeCounter);
}

function replayIdRejectsHostileReplacementCommands() {
  const store = new CacheStore([
    entry("api-v0", "api", 0),
    entry("media-v0", "media", 0),
    entry("images-v0", "images", 0),
  ]);
  const counter = new GenerationCounter();
  const first = runPurgeBatch(
    store,
    counter,
    "same-id",
    [new PurgeCommand("api"), new PurgeCommand("media")],
  );
  const afterStore = store.view();
  const afterCounter = counter.view();
  const replacements = [
    new PurgeCommand("images", { failAfterPurge: true }),
    new PurgeCommand("api", { failAfterPurge: true }),
  ];
  const second = runPurgeBatch(
    store,
    counter,
    "same-id",
    replacements,
  );
  return first.ok
    && second.ok
    && second.skipped
    && same(replacements.map((command) => command.preparation()), [null, null])
    && same(store.view(), afterStore)
    && same(counter.view(), afterCounter);
}

function repeatedScopeCutoffsAreRecomputedOnRetry() {
  const store = new CacheStore([
    entry("api-v4", "api", 4),
    entry("api-v5", "api", 5),
    entry("api-v7", "api", 7),
    entry("media-v1", "media", 1),
    entry("media-v3", "media", 3),
  ]);
  const counter = new GenerationCounter({ api: 4, media: 1 }, ["older"]);
  const commands = [
    new PurgeCommand("api"),
    new PurgeCommand("media"),
    new PurgeCommand("api", { failAfterPurge: true }),
  ];
  const beforeStore = store.view();
  const beforeCounter = counter.view();
  const first = runPurgeBatch(store, counter, "cutoff-retry", commands);
  const rolledBack = same(store.view(), beforeStore)
    && same(counter.view(), beforeCounter);
  commands[2].failAfterPurge = false;
  const replay = runPurgeBatch(store, counter, "cutoff-retry", commands);
  return !first.ok
    && rolledBack
    && replay.ok
    && !replay.skipped
    && same(replay.purged, ["api-v4", "media-v1", "api-v5"])
    && same(store.view(), [
      entry("api-v7", "api", 7),
      entry("media-v3", "media", 3),
    ])
    && same(counter.view(), {
      generations: { api: 6, media: 2 },
      completed: ["older", "cutoff-retry"],
    });
}

process.stdout.write(JSON.stringify([
  rollbackAfterSeveralPurges(),
  rollbackKeepsPreparedBaseline(),
  precompletedBatchNeverPreparesCommands(),
  replayIdRejectsHostileReplacementCommands(),
  repeatedScopeCutoffsAreRecomputedOnRetry(),
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
