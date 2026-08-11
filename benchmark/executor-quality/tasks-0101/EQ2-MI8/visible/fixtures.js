import { ArtifactRegistry } from "./registry-store.js";
import { SchemaCheck, SchemaDiagnosticJournal } from "./schema-check.js";
import { PublishTokenGate } from "./token-gate.js";

export function createRegistryFixture() {
  const journal = new SchemaDiagnosticJournal();
  return {
    tokenGate: new PublishTokenGate([
      { id: "north-publisher", actorId: "builder-1", active: true, namespaces: ["north"] },
      { id: "south-publisher", actorId: "builder-2", active: true, namespaces: ["south"] },
      { id: "expired-publisher", actorId: "builder-1", active: false, namespaces: ["north"] },
    ]),
    schemaCheck: new SchemaCheck(journal),
    registry: new ArtifactRegistry(),
    journal,
  };
}

export function validPublication(overrides = {}) {
  return {
    tokenId: "north-publisher",
    namespace: "north",
    artifactVersion: "2.4.0",
    manifest: {
      schemaVersion: 2,
      attributes: [
        { field: "name", value: "command-line-tools" },
        { field: "digest", value: "sha256:44c0" },
        { field: "mediaType", value: "application/vnd.example.bundle" },
      ],
    },
    ...overrides,
  };
}
