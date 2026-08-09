import assert from "node:assert/strict";
import test from "node:test";

import { CacheStore } from "../cache-store.js";
import { GenerationCounter } from "../generation-counter.js";
import { PurgeCommand } from "../purge-command.js";

test("prepares one cutoff and applies it to its scope", () => {
  const store = new CacheStore([
    { key: "stale", scope: "api", generation: 0 },
  ]);
  const counter = new GenerationCounter();
  const command = new PurgeCommand("api");

  const generation = command.prepare(counter);
  assert.equal(generation, 1);
  assert.deepEqual(command.execute(store, generation), ["stale"]);
  assert.equal(command.prepare(counter), 1);
});
