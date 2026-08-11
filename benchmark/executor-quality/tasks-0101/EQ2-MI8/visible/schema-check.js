const SUPPORTED_VERSIONS = new Map([
  [1, ["name", "digest"]],
  [2, ["name", "digest", "mediaType"]],
]);

const KNOWN_FIELDS = new Set(["name", "digest", "mediaType"]);

const REASON_PRIORITY = {
  unsupported_version: 0,
  missing_field: 1,
  wrong_type: 2,
};

export function collectSchemaIssues(manifest) {
  const attributes = Array.isArray(manifest.attributes) ? manifest.attributes : [];
  const required = SUPPORTED_VERSIONS.get(manifest.schemaVersion) ?? ["name", "digest"];
  const issues = [];

  if (!SUPPORTED_VERSIONS.has(manifest.schemaVersion)) {
    issues.push({
      reason: "unsupported_version",
      field: "schemaVersion",
      arrivalIndex: attributes.length,
    });
  }

  const seen = new Set();
  attributes.forEach((attribute, arrivalIndex) => {
    if (!KNOWN_FIELDS.has(attribute.field)) {
      return;
    }
    seen.add(attribute.field);
    if (typeof attribute.value !== "string") {
      issues.push({ reason: "wrong_type", field: attribute.field, arrivalIndex });
    }
  });

  required.forEach((field, requiredIndex) => {
    if (!seen.has(field)) {
      issues.push({
        reason: "missing_field",
        field,
        arrivalIndex: attributes.length + requiredIndex,
      });
    }
  });
  return issues;
}

export function rankSchemaIssues(issues) {
  return [...issues].sort((left, right) => left.arrivalIndex - right.arrivalIndex);
}

export class SchemaDiagnosticJournal {
  entries = [];

  append(entry) {
    const stored = Object.freeze({ ...entry });
    this.entries.push(stored);
    return stored;
  }
}

export class SchemaCheck {
  constructor(journal) {
    this.journal = journal;
  }

  inspect(namespace, artifactVersion, manifest) {
    const issue = rankSchemaIssues(collectSchemaIssues(manifest))[0] ?? null;
    if (issue === null) {
      return null;
    }
    return this.journal.append({ namespace, artifactVersion, ...issue });
  }
}
