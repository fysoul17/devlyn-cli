---
complexity: high
---
# Recoverable, exclusive CLI skill installation

Upgrade the real `bin/devlyn.js` function `installSkillsForCLI(cliKey)` so a failed
multi-skill installation leaves the prior installation usable. This function is
called by the existing CLI installation flow. Keep its synchronous API, return
count, unknown-CLI no-op, existing naming/alias rules, final directory stamping,
complete-bundle check and marker schema. No new user-facing flag or dependency.

Requirements:

1. Treat one invocation's selected skill directories, existing installation marker,
   and deprecated paths removed by its existing cleanup as one recoverable update.
   On success fully replace selected skills (remove stale files), perform the same
   deprecated cleanup, then expose a complete new marker. Preserve unrelated files,
   user-installed skills and every source file. Stamp Markdown with final installed
   paths, never temporary paths. Existing physical aliases must not remain alongside
   their canonical replacements. Preserve symlinks in unrelated user content without
   following or rewriting their targets.
2. Preflight, copying, stamping, validation or publication may throw. If one ordinary
   filesystem operation fails and subsequent recovery operations can succeed, restore
   all preexisting managed/deprecated paths and marker with exact bytes and file modes;
   remove newly created managed paths. Propagate an actionable failure to the caller;
   never report success on partial install. An initially absent skills directory must
   again be absent after failure. Do not require rollback after successful commit if
   only disposal of backup data fails: report that cleanup failure and keep recovery
   data, instead of concealing it. Never swallow a failed rollback or remove its only
   recovery copy. This is recoverability at function return, not an atomic snapshot
   for unrelated readers while publication is in progress.
3. Exclude simultaneous cooperating installations to the same destination with an
   exclusive filesystem lock acquired before inspecting or mutating destination
   contents. Another process or reentrant invocation must fail promptly with a clear
   busy error and leave the owner's lock/data intact. Calls targeting different
   directories must not block each other. Release only the current invocation's lock
   on success or ordinary failure; a later invocation must work. An existing lock is
   never assumed stale or stolen. Lock naming is internal; the supplied tests discover
   contention by entering the function again, not by assuming a filename.
4. Remove task-created staging/backup/lock debris after successful installation or
   successful recovery. Preserve original content outside the owned paths. Do not
   change installClaudeCore, instructions installation, other commands or global
   settings. Process crashes, power loss/fsync durability, malicious noncooperating
   writers, and changes to selected source trees during an install are out of scope.

Allowed implementation files: `bin/devlyn.js`, and a focused helper under `bin/`
only if needed. Optional regression checks may be added as `tests/regression*.js`.
Preserve supplied `tests/`, spec files, package.json and .gitignore byte-for-byte.
Use Node's standard library. The test loader exposes the existing function in a
VM and redirects source/destination to temporary fixtures; do not add exports solely
for tests or invoke a real user installation. All task tests must use disposable
fixtures. The root research owner handles local-only experimental delivery.

## Verification

Run `node --test tests/acceptance.js`. Add and run focused interaction checks for
partial publication followed by failure, successful retry, and same-target versus
different-target contention. Check prior marker/content/modes and unrelated symlinks
after recovery, not only thrown errors. Keep all temporary output out of the source.
