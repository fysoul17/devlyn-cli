# Artifact publication contract

Artifact publication must authorize an active publish token for the target namespace before schema inspection, schema failures rank unsupported-version before missing-field before wrong-type with declaration order breaking same-reason ties, and an unauthorized malformed publication must return the authorization failure without appending a schema diagnostic or registry version.

Publish tokens are scoped to registry namespaces. A missing, inactive, or out-of-scope token returns `{ "ok": false, "error": "publish_denied" }` without disclosing anything about the submitted artifact.

The registry accepts schema versions 1 and 2. Version 1 requires string `name` and `digest` declarations; version 2 also requires a string `mediaType`. A rejected schema appends exactly its selected diagnostic. Successful publication appends one immutable registry version.
