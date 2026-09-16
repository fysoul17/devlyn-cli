# Recoverable instruction-file migration

Change only `bin/devlyn.js::installInstructionsForCLI(cliKey)` (and optional new
`tests/regression*.js`) to make instruction installation recoverable and exclusive.
This is the real existing function, exposed by the supplied VM loader. Keep its
synchronous API and unrelated source bytes. No new dependencies or CLI options.

1. Preserve existing behavior: unknown/unsupported target returns false; existing
user instructions without the legacy marker stay byte-identical and return false;
legacy content is stripped using the existing helper plus one final newline;
missing destination copies the packaged template verbatim, or returns false if
that template is missing. Return true only after a successful write.
2. A reader of the destination must see a complete old or complete new file, never
a truncated/intermediate file. Stage in the destination filesystem and publish via
atomic rename. Preserve existing file permission bits. Fresh files use the normal
0666-and-umask mode. Unrelated paths and bundled source must remain unchanged.
3. Existing destination symlinks to regular files must retain the symlink itself
and update the physical referent; relative links and symlinked ancestors work.
Dangling links and nonregular destinations fail explicitly without mutation.
Hardlink identity, hostile concurrent symlink retargeting, crashes, fsync/power-loss
durability and noncooperating external writers are out of scope.
4. Serialize all cooperating calls addressing the same physical destination,
including other CLI keys and symlink aliases. Use an exclusive directory at the
physical destination filename plus `.devlyn-lock`. Refuse an occupied lock promptly
with an actionable busy/lock error; never steal it. Distinct files remain independent.
Read/decide/stage/publish/rollback are protected until all shared-path work is done.
5. Any single filesystem-operation failure before successful lock release,
including the release itself, must throw and restore the original destination's
bytes/mode or absence. Under this one-shot fault model subsequent recovery operations
succeed, no owned lock/temp residue remains, and a retry works. The original source
and foreign lock are never removed. If recovery itself also fails, report the
original and recovery errors explicitly and retain recoverable data; do not claim
success. Once lock release succeeds, failure disposing only private temporary or
backup files may keep the new destination but must visibly report cleanup failure.
This exception does not include lock removal or shared destination cleanup.
6. Add meaningful regressions as needed; run `node --test tests/acceptance.js`
and your additions. Do not modify supplied checks, spec or package metadata.
The containing directory already exists; creating directory trees is out of scope.
