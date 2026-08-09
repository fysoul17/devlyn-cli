import assert from "node:assert/strict";
import test from "node:test";

import { CacheStore } from "../cache-store.js";
import { GenerationCounter } from "../generation-counter.js";
import { runPurgeBatch } from "../purge-batch.js";
import { PurgeCommand } from "../purge-command.js";

test("a completed purge batch is skipped when replayed", () => {
  const store = new CacheStore([
    { key: "stale", scope: "api", generation: 0 },
  ]);
  const counter = new GenerationCounter();
  const commands = [new PurgeCommand("api")];

  assert.deepEqual(runPurgeBatch(store, counter, "batch-a", commands), {
    ok: true,
    skipped: false,
    purged: ["stale"],
    error: null,
  });
  assert.deepEqual(runPurgeBatch(store, counter, "batch-a", commands), {
    ok: true,
    skipped: true,
    purged: [],
    error: null,
  });
});
