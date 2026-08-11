#!/usr/bin/env python3
"""Evaluate artifact publication behavior without writing to the supplied tree."""

import json
from pathlib import Path
import subprocess
import sys


WORKDIR = Path(sys.argv[1]).resolve()
RUNNER = r'''import { pathToFileURL } from "node:url";

const root = process.argv[1];
const load = async (name) => import(pathToFileURL(`${root}/${name}`).href);
const { createRegistryFixture, validPublication } = await load("fixtures.js");
const { publishArtifact } = await load("publisher.js");

const denied = { ok: false, error: "publish_denied" };
const same = (left, right) => JSON.stringify(left) === JSON.stringify(right);

function malformedPublication(overrides = {}) {
  return validPublication({
    manifest: {
      schemaVersion: 2,
      attributes: [
        { field: "name", value: 404 },
        { field: "mediaType", value: "application/vnd.example.bundle" },
      ],
    },
    ...overrides,
  });
}

function inactiveTokenStopsPublication() {
  const state = createRegistryFixture();
  const result = publishArtifact(
    state,
    validPublication({ tokenId: "expired-publisher" }),
  );
  return same(result, denied)
    && state.journal.entries.length === 0
    && state.registry.versions.length === 0;
}

function namespaceScopeStopsPublication() {
  const state = createRegistryFixture();
  const result = publishArtifact(
    state,
    validPublication({ tokenId: "south-publisher" }),
  );
  return same(result, denied)
    && state.journal.entries.length === 0
    && state.registry.versions.length === 0;
}

function distinctReasonsUseContractPriority() {
  const state = createRegistryFixture();
  const result = publishArtifact(state, malformedPublication());
  const entry = state.journal.entries[0];
  return same(result, {
    ok: false,
    error: "schema_rejected",
    reason: "missing_field",
    field: "digest",
  })
    && entry?.reason === "missing_field"
    && entry?.field === "digest"
    && state.journal.entries.length === 1
    && state.registry.versions.length === 0;
}

function equalReasonsUseDeclarationOrder() {
  const state = createRegistryFixture();
  const result = publishArtifact(
    state,
    validPublication({
      manifest: {
        schemaVersion: 2,
        attributes: [
          { field: "digest", value: 9 },
          { field: "name", value: false },
          { field: "mediaType", value: "application/vnd.example.bundle" },
        ],
      },
    }),
  );
  const entry = state.journal.entries[0];
  return result.reason === "wrong_type"
    && result.field === "digest"
    && entry?.arrivalIndex === 0
    && state.journal.entries.length === 1
    && state.registry.versions.length === 0;
}

function deniedMalformedRequestLeavesNoSchemaTrace() {
  const state = createRegistryFixture();
  const result = publishArtifact(
    state,
    malformedPublication({ tokenId: "expired-publisher" }),
  );
  return same(result, denied)
    && state.journal.entries.length === 0
    && state.registry.versions.length === 0;
}

process.stdout.write(JSON.stringify([
  inactiveTokenStopsPublication(),
  namespaceScopeStopsPublication(),
  distinctReasonsUseContractPriority(),
  equalReasonsUseDeclarationOrder(),
  deniedMalformedRequestLeavesNoSchemaTrace(),
]));
'''
INVARIANT = (
    "Artifact publication must authorize an active publish token for the target namespace before "
    "schema inspection, schema failures rank unsupported-version before missing-field before wrong-type "
    "with declaration order breaking same-reason ties, and an unauthorized malformed publication must "
    "return the authorization failure without appending a schema diagnostic or registry version."
)


completed = subprocess.run(
    ["node", "--input-type=module", "--eval", RUNNER, str(WORKDIR)],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
    timeout=10,
)
try:
    checks = json.loads(completed.stdout) if completed.returncode == 0 else []
except json.JSONDecodeError:
    checks = []
if len(checks) != 5 or any(type(value) is not bool for value in checks):
    checks = [False, False, False, False, False]

identifiers = ["axis1-a", "axis1-b", "axis2-a", "axis2-b", "interaction"]
print(
    json.dumps(
        {
            "manifestations": [
                {"id": identifier, "invariant": INVARIANT, "passed": passed}
                for identifier, passed in zip(identifiers, checks, strict=True)
            ]
        },
        separators=(",", ":"),
    )
)
