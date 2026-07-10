# F11 base snapshot

`source.bundle` contains the committed pre-task state from
`benchmark/auto-resolve/fixtures/test-repo`. It also contains that fixture's
pinned dependency tree because the untouched server imports Express and the
ceiling evaluator performs no package install. The hidden HTTP clients use
only Node core modules, so the fixture remains network-independent. They drive
the Express app through in-memory `IncomingMessage`/`ServerResponse` objects;
no TCP port is opened, while middleware and response behavior are still
exercised.

L3 classification: **KEYWORD-TRAP** (`atomic-state`). The source fixture's
notes identify `transactional`, `atomic`, and `rollback` as answer-revealing
terms. `task.txt` omits those triggers while retaining both observable
outcomes: a rejected request leaves `GET /items` unchanged, and a fully valid
request appends every item successfully.
