---
id: windows-portability-3.1.1
title: Repair native Windows installation and resolve execution
complexity: high
---

# Repair native Windows installation and resolve execution

## Context and prediction

The user supplied a native Windows npm install failure and a successful pipeline
only after local patches for locking, encoding, prompt transport and timeouts.
The original input compared logical colon skill names with npm's Windows
U+F03A extraction names (`bin/devlyn.js:362`), imports fcntl in bootstrap locking
(`resolve-bootstrap.py:367`), closes bounded subprocess stdin and kills POSIX
groups (`run-bounded.py:24`), and closes monitored Codex stdin. The current
mandatory outer helper also imports fcntl and fsyncs directories.

Prediction: correcting the filesystem/process/text boundaries will let the npm
package install and the named native Python harness operations execute on
Windows without user patches or PYTHONUTF8 setup, preserving existing POSIX
behavior, exact prompt/evidence bytes and fail-closed safety contracts.
Codex currently supports native Windows sandboxing; the supplied read rejection
is evidence for an inline read-only review route, not proof that Windows has no
sandbox. A real Windows runner is required before declaring Windows verified.

## Findings-backed outer iterations

Original input `4758808614ccfd3941c3ed7894e5726321bb9654` through unaccepted
checkpoint `a6782ffcc032deab796bdff6d71794e2a5110453` remains the full 53-path
product review surface. Run `rs-20260910T063702Z-2e30f88365b2` exhausted its
unchanged 4/4 budget and is preserved under `.devlyn/runs/` with verdict
`BLOCKED:build-gate-exhausted`; this amendment starts outer iteration 2 of 3.

Native CI `34461164783` on that checkpoint passed POSIX and 16 Windows
portability cases (one inapplicable skip), but failed the full bootstrap
self-test at `resolve-bootstrap.py:576`: `snapshot()` treats a dangling nested
junction as a file because `is_symlink()` is false. Its archived raw log SHA256
is `698f210ce53ba4dd2424ec3f449666e6a90ef59d9f74455cb130affe8750035e`.
Correct only this observed fixture boundary: snapshot root and nested, live and
dangling directory redirects as link identities without traversing their targets.
Preserve every refusal and before/after byte assertion. R1-R7 remain binding.

Bootstrap the new normal run from its actual committed HEAD. Owner inputs are
this linked spec amendment; inherited product changes remain unaccepted.
PLAN and both fresh judges receive a separately hashed original-to-checkpoint
diff and path manifest; both judges additionally receive the original-to-final
product diff and fresh-run diff. Seal whole-task scope and final-source identity
with mechanical evidence. Acceptance requires the full normal phase graph,
post-CLEANUP mechanical checks including separately sealed bootstrap self-test,
both independent judges, finish gate, successful archive and actual passing
POSIX/Windows CI on the final accepted source. Checkpoints alone are not passes.

Outer iteration 2 ended BLOCKED as run `rs-20260910T101056Z-8a1facf9f0ba`,
preserved with budget 0/4 and final report SHA256
`448a79b47b26855cf507e315351aceed6316a026ef95a9d3b7540dabb212361a`.
Checkpoint `6f7c6cfcf90b167d7135999d81f6d8953c5a6d3e` fixed the junction
snapshot and passed native CI `34466453563` (raw log SHA256
`736160489e3ce4bd3b1787dd9e7b7401bb52b431f9ac34aeddeadbd1746f66d2`).
The required pair judge hit a native session limit; the primary independently
found HIGH `VERIFY-PRIMARY-001`: `platform-support.py:106-107` skips Windows
tree teardown when the leader exits after timeout selection at line 156 but
before `finally`. The fixture at `scripts/test-windows-portability.py:363`
keeps the leader alive and does not cover surviving descendants in that race.

This amendment starts the final outer iteration 3 of 3. Preserve process-tree
ownership independently of leader lifetime, including the launch-to-ownership
boundary, without shell argument concatenation or orphan-prone PID rediscovery.
Use supported native primitives, preserve visible errors, normal child exit
codes, exact stdin/argv and existing POSIX behavior. A deterministic native
regression must order timeout selection, actual leader exit, and teardown while
a descendant remains live, then verify descendant cessation and return 124.
Retain the fixed root/nested live/dangling snapshot assertions and all inherited
checks. Full original-to-final 53-path review includes both unaccepted
checkpoints; owner spec amendments are separate inputs. The resumed required
pair judge must actually use `claude-fable-5-1`, through a task-local model-only
role profile and matching native evidence; global pins/settings stay unchanged.

## Requirements

1. Install core and optional skills on native Windows from actual npm tar
   extraction, including Claude and Codex/shared-agent targets and reinstalls.
   Resolve logical colon identifiers to legal physical paths at the boundary;
   preserve skill frontmatter names, managed cleanup, complete-install markers,
   installed runtime stamps and unrelated user skills. Reject ambiguous aliases
   or genuinely incomplete installs. Handle the existing U+F03A package layout.
2. Bootstrap and mandatory task completion must use native supported locking.
   Preserve exclusive ownership, distinguish contention from unavailable locking,
   release on every exit, and retain Windows cleanup conservatively when process
   state cannot be proved. Correct directory flush assumptions without disabling
   file durability, ownership checks or weakening deletion/publication gates.
3. All shipped Python harness text and subprocess decoding used by these flows
   must use UTF-8 without requiring user environment settings, including Korean
   text and adapter punctuation under cp949/non-UTF8 locale defaults. Select the
   smallest auditable fix after examining entrypoints/imports; do not install
   global monkey patches or silently replace undecodable evidence bytes.
4. Add `run-bounded.py <seconds> --stdin-file <path> -- <cmd> [args...]` support
   using the input file's exact bytes. Absent this option retains DEVNULL.
   Reject invalid/missing input before dispatch with a visible error. Preserve
   child exit codes. Native Windows timeouts terminate the child process tree
   and return 124; POSIX TERM/KILL and no-surviving-descendants semantics remain.
   Resolve Windows npm command shims safely for the documented engine commands;
   do not concatenate arbitrary arguments into an injectable shell command.
5. Add explicit `DEVLYN_CODEX_PROMPT_FILE` transport to codex-monitored.sh,
   preserving DEVNULL when absent. File transport supplies the sole prompt via
   stdin (explicit `-`); reject competing prompt arguments, missing/unreadable
   files and receipt file/prompt mismatches before model launch. Bind the exact
   delivered prompt bytes and actual argv in invocation/judge evidence. Preserve
   isolation, requested models, capabilities, timeout handling and existing
   receipt integrity. Audit receipt process helpers for native Windows blockers
   exercised by this transport, fixing those required for the supported route.
6. Update the canonical bounded/monitored invocation documentation and callers
   to use file transport for multiline prompts on Windows. For constrained
   Windows Codex judge reads, the orchestrator supplies spec, expected contract,
   diff, relevant source/tests and sealed verification evidence inline, with
   explicit instructions to judge that supplied material without running tools.
   Keep `-s read-only`, isolation, freshness and bounded judge contracts; never
   widen sandbox permissions or invent successful evidence. Insufficient inputs
   produce a visible blocked finding. Do not claim all Windows reads are denied.
7. Remove ASCII-colon assumptions from the relevant bootstrap self-test fixture
   lookup and add meaningful portability regressions. Add minimal CI that packs
   on a POSIX runner then installs/tests that artifact on native Windows with
   native Python and Node. Do not depend on a full colon-containing Git checkout
   on Windows. Exercise Korean/non-ASCII payloads, lock contention and lock
   failure, command shim execution, prompt byte identity, timeout child trees,
   markers/reinstall behavior and evidence tamper rejection. Keep existing
   POSIX checks and mirror parity passing; no model credentials in CI.

## Authorized product surface

- bin/devlyn.js
- config/skills/_shared/*.py, codex-monitored.sh, codex-config.md,
  engine-preflight.md and adapters/claude.md, adapters/codex.md
- config/skills/devlyn:resolve/SKILL.md and references/task-completion.md,
  references/phases/surface-close.md and references/phases/verify.md
- Exact .agents/skills mirrors of changed canonical skill files
- scripts/lint-skills.sh and scripts/test-windows-portability.py
- .github/workflows/portability.yml and README.md

Python edits outside the named failing helpers are limited to explicit UTF-8
I/O or directly exercised Windows process/path blockers. PLAN must enumerate
the actual paths. A small shared platform helper is authorized only if observed
duplicate boundaries justify it. No version bump, release publication, engine
pin changes, research artifacts, global configuration changes or unrelated
cleanup. The outer owner coordinates actual Windows CI and release separately.

<!-- devlyn:verification -->
## Verification

- `python3 scripts/test-windows-portability.py` exits 0. It exercises real
  installer and subprocess boundaries, exact non-ASCII stdin bytes, absent-file
  rejection without child execution, lock contention versus unavailable locks,
  prompt/evidence mismatch rejection, legacy transport and process-tree timeout.
  Native Windows includes deterministic timeout-selection → leader-exit → tree
  teardown ordering, descendant cessation, normal leader exit with descendants,
  and error/launch ownership boundaries; successful leaders retain exit codes.
  Platform-specific tests run on their actual platform and identify skips.
- `python3 config/skills/_shared/resolve-bootstrap.py --self-test` exits 0,
  including root/nested live/dangling redirect refusal and unchanged snapshots.
  Capture this full command separately in BUILD_GATE and post-CLEANUP evidence.
- `python3 config/skills/_shared/task-complete.py --self-test` exits 0.
- `bash scripts/lint-skills.sh` exits 0 with existing checks intact and canonical
  mirrors identical; `git diff --check` exits 0.
- The added CI executes the packed artifact on native Windows using Node and
  native Python, with UTF-8 mode disabled for the encoding regression. Source
  verification and Windows execution evidence are reported separately. The outer
  owner must observe a passing Windows job on the accepted source before release.
- Independent review checks all binding clauses, including aliases, lock error
  classification, input bytes, shell injection, descendant termination, receipt
  tampering and unchanged read-only judge/ownership guarantees.
