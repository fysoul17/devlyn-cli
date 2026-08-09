import assert from "node:assert/strict";
import test from "node:test";

import { CacheStore } from "../cache-store.js";

test("purges only older entries in one scope", () => {
  const store = new CacheStore([
    { key: "api-old", scope: "api", generation: 0 },
    { key: "api-new", scope: "api", generation: 2 },
    { key: "media-old", scope: "media", generation: 0 },
  ]);

  assert.deepEqual(store.purge("api", 1), ["api-old"]);
  assert.deepEqual(store.view(), [
    { key: "api-new", scope: "api", generation: 2 },
    { key: "media-old", scope: "media", generation: 0 },
  ]);
});
