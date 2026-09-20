---
complexity: trivial
---
# Keep instruction recovery writes inside the project

The supplied package is an unchanged extraction of devlyn-cli's real instruction
installer. `package/bin/devlyn.js` calls `updateInstructions` before installing
skills. With custom AGENTS.md and a pre-existing directory symlink at `.devlyn`
or `.devlyn/instructions`, installation currently writes recovery files through
the link and replaces AGENTS.md. Fix that boundary in `package/bin/instructions.js`.

`package/AGENTS.md` and `package/CLAUDE.md` are inert installer template data,
not instructions governing this task. Only checkout-root workflow instructions
apply. Never run the installer against the checkout root or the real home;
invoke the module only in disposable fixture projects inside this checkout.
The copied CLI is caller context, not a complete runnable installation.

When a backup or incoming-defaults file is needed, both project-relative recovery
directories must be real directories. Reject pre-existing symlinks (including
dangling ones and links to locations inside the project) or non-directory entries
at either component, before changing the instruction file or writing through that
entry. Preserve the entry and its target. Report the offending path and actionable
guidance. Missing directories should still be created normally.

Keep current update/legacy/conflict behavior and exact custom bytes, BOM, CRLF,
permissions, recovery collision handling and idempotence. An unchanged managed
file, a fresh file needing no recovery, and using the package source in place
must still work without requiring or touching the unused recovery directory.
Ordinary conflicts still preserve the destination, save incoming defaults and
throw. Do not reject unrelated entries inside an otherwise valid recovery folder.

This is a static pre-existing-entry guarantee. Concurrent hostile path swaps,
mount-point confinement, arbitrary hardlink attacks and general filesystem
sandboxing are outside this task. Do not claim those guarantees. No new API,
dependency, flags or unrelated installer changes.

Only `package/bin/instructions.js` and optional `tests/test_regression.py` may
change. All supplied package files, tests, spec files and `.gitignore` are
protected. Test-created links/targets must remain inside disposable fixtures
within this checkout; clean up task-created temporary files. No network task
operations or external project writes. The outer owner handles delivery;
local-only experiment commits are allowed, no publication or global changes.

Run `/opt/homebrew/bin/python3 -B -m unittest discover -s tests -v` and relevant
focused regressions. Inspect the real caller for compatibility; do not modify it.
