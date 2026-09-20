# Preserve invalid project engine configurations

The supplied package contains devlyn-cli's real role-configuration helper, its
adapters and real callers. Users whose project `.devlyn/engines.json` is a link
whose target was removed currently get a successful default-engine status; setting
a role replaces that unresolved link. Correct this behavior in
`package/role-config.py`.

Only a genuinely absent optional configuration may use defaults. A dangling
configuration-file link, directory in place of the file, non-directory ancestor,
link loop, permission denial or other filesystem read error must report
`BLOCKED:invalid-engine-config` with the configuration path. Status, dispatch
resolution, role edits (including clear), and explicit `--role-config` must not
silently treat these as a fresh configuration. Rejected edits preserve the entry,
its link text/target and unrelated files. No partial config or temp residue.

Preserve genuinely absent optional files, including an absent `.devlyn` directory;
required missing files still fail. Preserve valid configuration symlink reads,
exact source/digest bindings, normal edits, custom fields, validation, selection
precedence, no-pair/status behavior and the existing self-tests. A successful edit
of a valid link keeps its existing behavior: replaces the link with the updated
project file and leaves the old target unchanged. Do not forbid all links or
change the public API, CLI, error prefix, engine policy or dependencies.

This concerns synchronous filesystem errors and pre-existing leaf entries with
valid directory ancestors (plus explicit non-directory/loop error cases).
Concurrent path swaps, deleted-after-read inputs, dangling directory ancestors,
crash durability and general filesystem confinement are outside this task.

Only `package/role-config.py` and optional `tests/test_regression.py` may change.
All supplied other sources, tests, spec files and `.gitignore` are protected.
Inspect relevant callers for compatibility. Use disposable fixtures inside this
checkout and remove task-created temporary files. No network task operations,
external project access, global changes or publication; local commits allowed.
The outer owner handles delivery. Do not invoke resolve or any skill pipeline.

Run `/opt/homebrew/bin/python3 -B -m unittest discover -s tests -v`,
`/opt/homebrew/bin/python3 -B package/role-config.py --self-test`, and relevant
focused regressions. No native engine/model call is needed for these checks.
