<!-- Template, filled mechanically per task: {ID}, {REPO} clone directory name, {W} the workspaces root, {NODE_NOTE} the node_modules note or empty, {TOOLCHAIN} the provisioned command prefix and test command. -->
# Phase C: implement one request's reference, twin and hidden oracle

You implement specifications written by a corpus author for a code-review evaluation. Your task: **{ID}** for repository **{REPO}**.

Inputs (read-only): `{W}/author/corpus/{ID}/` — `spec.md`, `spec.expected.json`, `hidden/implementation.md`, `hidden/oracle.md`, `hidden/mechanism.md`. Do not read any other file outside `{W}/author/corpus/{ID}/`, `{W}/author/repos/{REPO}/` and your workspace; nothing else is relevant, and you have no web access.

Workspace (writable): `{W}/impl/{ID}/`. It holds `tree/`, a git repository whose single commit `base` is the pinned repository tree{NODE_NOTE}.

Produce, in the workspace:
1. `reference.patch` — `git diff base` output (from `tree/`) of a correct, idiomatic, complete implementation of `spec.md` exactly as `hidden/implementation.md` (a) describes, including the tests it names (added to the repository's own test suite). Nothing else: no generated files, caches or coverage output.
2. `twin.patch` — the same implementation with exactly the one deviation `hidden/implementation.md` (b) describes, changing exactly the same set of files as `reference.patch`. No comment, name or other trace may hint at the deviation; everything else is byte-identical to the reference.
3. `oracle/` — an executable hidden oracle implementing every row of `hidden/oracle.md`: `oracle/run.sh <tree>` runs all rows against the tree at path `<tree>` and prints exactly one JSON object `{"rows": {"<row id>": true|false, ...}}` on stdout (true = the row's expected result holds), exit 0 when it ran, non-zero only if it could not run. It must not modify `<tree>` (write any scratch files to a temporary directory) and must not use the network.
4. `NOTES.md` — anything in the specification you could not follow exactly, and why (empty if none).

Check before finishing, using the toolchain: {TOOLCHAIN}
- with `reference.patch` applied to a fresh copy of `base`: every command in `spec.expected.json` `verification_commands` passes, and `oracle/run.sh` reports every row true;
- with `twin.patch` applied instead: every verification command passes, and `oracle/run.sh` reports exactly the designated witness row false and every other row true;
- the two patches touch the same file set.
If a check fails, fix your implementation; if the specification itself makes it impossible, say so in `NOTES.md` rather than bending the rules.
