# 0262 design — self-observation loop for user-facing changes

Status: design converged (root, Astra ultra and Grok 4.7, three rounds); owner decisions recorded 2026-10-28. The candidate is implemented on `feat/ui-observation-loop`. The evidence-flow smoke prediction below was frozen before any smoke run.

## Why

The owner reported that the harness finds intent, implements, reviews and improves code well, but user-facing work escapes with:
- missing features;
- no polish;
- errors;
- results that do not match the first request.

**What escaped.** Mining six of the owner's private repositories found 21 shipped UI defects that were later fixed. The repository names and changes stay private; only the counts are recorded here.

| Class | Count |
|---|---:|
| A, explicit request omitted | 0 |
| B, implicit states (failure, narrow width, platform) | 7 |
| C, runtime errors the source and tests did not show | 4 |
| D, layout | 6 |
| E, intent mismatch | 2 |
| F, internals shown on screen | 2 |

Twelve would have been caught by comparing a capture of the product with the request, seven only by running the real application or production build (mocked IPC and dev servers hid them), and two by better planning. None of the originating changes records any visual check. These counts establish existence and class mix, not a rate.

**Root cause, agreed by all three.** "Done" is verified at the source boundary: build, tests and self-written review records. Nothing requires observing the product where its user receives it.

For the owner's pinned executor this was also impossible. Under Codex's `workspace-write` seatbelt on macOS:
- Chrome exits 134 and the headless shell exits 133;
- `simctl`, `screencapture` and window listing are denied.

`codex-monitored.sh` rightly forbids leaving the sandbox.

## Candidate C — one mechanism, attributed as a whole

1. **Obligation.** An `Observation` bullet in the installed Quick Start, identical in CLAUDE.md, AGENTS.md and runtime-principles.md. Before calling a user-facing change done, the executor:
   - runs the product built from it where its user receives it;
   - walks each requested journey through the affected states in representative target cases;
   - compares the captures with the original request;
   - repairs and rechecks.

   A required journey that could not be observed is not done. Every unobserved case is reported as `NOT OBSERVED: <case> — <probe tried>`. The bullet names no tool, so it applies to web, native, Flutter, games, terminals, files and messages alike.
2. **Capability.** `_shared/observer.py` runs the implementer's observation commands outside the executor's sandbox, through a file spool:
   - **Drain:** it serves `<receipt dir>/observe` while the executor runs, and the packet's `observe` argv tells the executor how to call it.
   - **Direct:** the orchestrator wraps the Codex call with `observer.py run` (adapters/codex.md).
   - Each command runs once in the task worktree with a fresh `DEVLYN_OBSERVATION_DIR`. Its process tree is then ended, and the reply carries raw outcome, digests and the file inventory. The observer never judges; the implementer does.
   - Liveness is a lock held for the server's lifetime, so a dead server fails the call fast instead of hanging it.
3. **Evidence.** `acceptance.py` retains every regular file under `.devlyn/loop/evidence/observations` on every path, including failure. A link fails acceptance. Custody hashing now streams, so large captures cannot exhaust memory.
4. **Gap rule.**
   - **Drain:** a required journey that cannot be observed is a `needs-review` blocker. A supplemental gap goes in `assumptions` as `NOT OBSERVED: …`.
   - **Direct:** the same line goes in the final report, and the change is not done.

**Not in C:**
- planner-declared journeys or always-rerun checks: a rerun after submission cannot be repaired;
- an independent observer/reviewer;
- a per-surface cookbook;
- new report headings;
- submission schema changes.

The two later rungs (planning journeys, then an independent look) each need a residual that C leaves.

## Owner decisions (2026-10-28)

1. **Yes:** an isolated, capture-only observer may run app and test commands outside Codex's sandbox, on fixture data. It never uses the owner's desktop, browser profile or accounts.
2. **Hold:** a mandatory journey that cannot be observed holds delivery; supplemental gaps are disclosed.
3. **Mandatory rows:**
   - requested journeys;
   - relevant error and recovery behaviour;
   - usable layout at target sizes;
   - the existing no-TMI rule.
4. **Corpus:** owner replays, after qualification.
5. **Blind rating:** about 30 minutes of owner blind rating of pilot outputs.
6. **Scope:** this is a mechanism study, authorized as an exception to the 2026-10-28 stop of the instruction-wording line, including its rule text.

## Verification

1. **Evidence-flow smoke** (C only; both engines × both paths, plus one route-less run). The frozen prediction, adopted from Astra:

   > On supported routes, fresh evidence reaches the executor before submission, the executor inspects it, and a detected violation reaches repair and recheck. Unavailable routes leave a visible, durable gap rather than an observed pass.

   If it fails on a supported route, stop: C does not implement self-observation there.

   The fixture is a small Vite + React list with two layout traps the request does not mention. A hidden witness, qualified against the unfixed app (fails), a reference fix (passes) and a partial fix (fails), judges each final tree. That witness is reported, not gated.
2. **Generality conformance probes**, each showing the right classification and retained captures:
   - Flutter on a real target runtime without Playwright;
   - a canvas game interaction;
   - a no-browser, no-network case.
3. **Paired pilot, B vs C:**
   - 2–4 owner replays from the original feature's parent, with the original request;
   - hidden witnesses qualified against the defective delivery and its later fix;
   - engines × paths × 2 replicates;
   - owner blind rating of every output;
   - the 0232 per-success guards, failures included;
   - a CLI inertness smoke;
   - the arm-neutral false-completion definition.

   The pilot can reject C; it cannot establish a modest general gain.
