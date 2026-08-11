import assert from "node:assert/strict";
import test from "node:test";

import { createRegistryFixture, validPublication } from "../fixtures.js";
import { publishArtifact } from "../publisher.js";

test("a valid scoped request publishes one registry version", () => {
  const state = createRegistryFixture();
  const result = publishArtifact(state, validPublication());
  assert.equal(result.status, "published");
  assert.equal(result.version.namespace, "north");
  assert.equal(state.registry.versions.length, 1);
  assert.equal(state.journal.entries.length, 0);
});

test("a valid request outside the token namespace is denied", () => {
  const state = createRegistryFixture();
  const result = publishArtifact(
    state,
    validPublication({ tokenId: "south-publisher" }),
  );
  assert.deepEqual(result, { ok: false, error: "publish_denied" });
  assert.equal(state.registry.versions.length, 0);
  assert.equal(state.journal.entries.length, 0);
});
