# 0189 — safe installed instructions and 3.1.3 release

2026-09-19. User authorized closing the existing-project upgrade gap and publishing
the entry correction. Root works directly, without invoking resolve. Mission1 and
0187's minimal-contract NO-GO remain unchanged; this is no new model-quality claim.

0188/PR63 changed packaged instructions and local entry surfaces, but npm remained
3.1.2. Existing AGENTS.md was preserved stale, while CLAUDE.md was overwritten.
Grok's global description was subsequently aligned with an exact backed-up delta;
that alone did not update other installations.

One shared installer now writes a checksummed managed block. Outside user text is
byte-preserved and takes precedence; exact originals are backed up under ignored
`.devlyn/instructions/`. Known unmodified 3.0.0–3.1.2 factory bodies migrate by hashes
computed from actual published tarballs, even with custom prefix/suffix or CRLF.
Modified managed blocks, ambiguous markers and recognizable edited legacy contracts
fail visibly with incoming defaults. Plain custom documents gain a managed block.
Symlinks, non-UTF8 input and conflicting recovery files fail with guidance. Source
checkout templates stay unwrapped; already wrapped package templates are rejected.
Claude updates CLAUDE.md; Codex/Grok/omp/Pi share AGENTS.md. Only selected targets
install skills. Reinstall is required; this is not a remote update of user projects.
Older installers retain their old destructive CLAUDE behavior; use3.1.3+ consistently.

**No workaround:** replace stale-preserve/whole-file-overwrite with explicit ownership,
not guessed three-way merging of arbitrary old user edits. **No overengineering:**
remove legacy end-of-file truncation, reuse one standard-library updater, add no
flags or merge dependency. Deleting checksum validation would allow silently losing
edits inside managed defaults; deleting legacy hashes would break safe old upgrades.

Prediction and evidence: `.devlyn/0189-release/`. Fourteen npm-packed PackageTests
cover all target installs, future managed upgrades, conflicts, exact recovery and
source-root execution. Thirty actual published-template cases cover twenty pristine
upgrades and ten edited-first-sentinel conflicts. Fable5.1 reviews are native,
tools-disabled calls with exact returned model identity; findings are adjudicated
against source and actual tests, not accepted on model authority. Lint initially
exposed an incomplete-source fixture missing instruction templates; the fixture now
includes them and still requires the intentionally absent skill to fail.

`FINAL.md` in the evidence directory records final review/check outcomes, exact PR,
merge/tag, public npm artifact identity, installed-artifact verification and cleanup.
Publication is not established by the version bump in this report. Next research
remains the approved instruction-priority and actual review-to-repair intervention.
