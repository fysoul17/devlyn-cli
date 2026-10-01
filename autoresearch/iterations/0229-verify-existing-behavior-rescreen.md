# 0229 — meet "existing … behavior" by matching the base's existing operation, then re-run the 0228 gates and the fresh re-screen

2026-10-01. **Status: REGISTERED (Astra FREEZE).** Frozen before the H commit, any replay call and any corpus authoring. Runs only after the owner approves.

Registration review: Astra R0 REVISE (3) + three Claude critics (diagnosis, recall, subtractive) → R1 FREEZE (`.devlyn/0229/reg-*`).

**Owner decision (2026-10-01, through the devlyn-os-v1 session):** after 0228's R2 FAIL, diagnose why the Codex primary still blocked the correct J4 reference, fix it and prepare a re-screen. Stop for approval before any run. Keep the judge account `_devlynjudge`, its current token and Addendum C2's isolation. No resolve invocation.

0229 amends [0228](0228-verify-rubric-rescreen.md) by reference. Anything not named here stays as 0228 registered it, with Addenda C1–C3.

## Why this iter exists

- **Pre-flight 0:** 0228's R2 failed on one G block of the correct J4 reference (C3).
  - In the [0228 diagnosis](../experiments/0228/diagnosis/DIAGNOSIS.md), that seat had the base's deferral in view. It bound the deferral as a violation of "the existing eviction disposal behavior", read as a new requirement.
  - The one G seat that compared with the base's other set-triggered evictions reported the same scenario as advisory.
  - The rubric never says that the existing-behavior part of a clause is met by matching the base's existing operation, nor that this behavior is not itself a defect under that part.
  - The cause is a hypothesis among three: scope, pre-existing-defect framing, chance.
- **#7 Mission-bound:** as 0227/0228.

**0229 decides one thing:** whether 22616b57 + F + G + H may re-enter development of steps 2–5. The limits are 0228's ("decides one thing"), plus one: the gates cannot show that H caused a change.

## Candidate

**H** is one commit on G (`607c3cf7`), on a pushed branch `candidate/0229-fix` with no PR, mirrored byte for byte into `.agents/skills`. Addendum D1 names H before any replay. `V` = `607c3cf7:config/skills/devlyn:resolve/references/phases/verify.md`.

H replaces G's preservation sentences, V:87–95 (from "For a clause that requires an existing path's current behavior" to "must leave unchanged."), with:

> For the part of a clause that requires existing behavior — an existing path's current behavior, or "the existing …" behavior a new path must receive — establish that behavior from `base_sha` (the snapshot diff's base side): for an existing path, the same operation, or unchanged code on the path the clause names; for a new path, the existing operation that performs the named behavior under the same options. That part is met by matching it: bind only a demonstrated departure, and do not treat the existing behavior itself as a defect under that part. A public contract that this behavior already contradicts binds separately only if the task independently requires conformance or the diff introduces or changes that promise; otherwise report the conflict as advisory. Agreement with `base_sha` never excuses a requirement the base does not already meet: the rest of such a clause, every other new requirement, and any state a new or failing operation must leave unchanged stay binding.

V:85–86 ("Small impact, rare inputs, or a pre-existing defect do not excuse that violation.") stays unchanged. A deviation from the base on a concrete required property remains a violation.

**Obligations, as for 0228's G:**
- lint and the portability suite pass;
- a grep finds no 0227 task word in the diff;
- Astra SHIP of `git diff 607c3cf7 H`.

## Gates (development evidence; never a 0227 regrade)

As 0228's "Gates before authoring" with C1–C3, with H in place of G and the following changes.

**Inherited from 0228 and C2:**
- replays of 0227's pristine rounds run as the judge account;
- inventory and a judge open-check before every batch;
- process control by uid, with the kernel-verified OS-agent exception;
- a credential check after every attempt;
- the owner's baseline compare after every batch;
- masked labeling with an Astra blind audit, doubt counting against the gate;
- the account-drift rule.

**Changes, all fixed in D1 before any call:**

- **Runner (D1):**
  - arms F and H, with H staged from `git archive H config/skills` as `product-H`;
  - attempt folders under `DEV/H/…`;
  - the collector pools every finding of any rank on twin replays, INFO included, so R3's demotion check sees lower-rank target findings;
  - Astra SHIP of the runner diff.
- **R1 (apparatus):**
  - H's product differs from 0227's only in `verify.md`;
  - prompt equality for all 64 tokens (rubric frame = H's `verify.md`);
  - stub replay 64/64 as the judge;
  - the isolation probe and the owner's baseline compare run again, because the runner changes;
  - Astra SHIP.
- **R2 (J4 references)** concentrates on where blocks occur: all five R2 blocks came from Codex primaries on the codex-orientation rounds.
  - **Replays, interleaved in a D1 order:**
    - H ×15 for each of the two codex-orientation J4 reference rounds (30);
    - H ×5 for each of the two claude-orientation J4 reference rounds (10);
    - F ×8 for each of the two codex-orientation rounds (16).
  - **PASS** iff every H replay is a clean reference with no diagnosed J4 block **and** at least 3 of F's 16 replays contain a diagnosed J4 block.
  - **INCONCLUSIVE:** every H replay is clean, but F has fewer blocks.
  - **FAIL:** anything else.
- **R3 (recall and breadth):** 100 replays under H, including the per-seat demotion check on twin replays.
  - The other 60 rounds once each.
  - Two more replays of each J2, J3, J4, P2 and P3 twin round (40). J2 is added because its twin, like J3's, behaves like the base in its trigger scenario while violating a required property, which is H's recall risk.

FAIL or INCONCLUSIVE stops the work and goes to the owner, as in 0228.

## Corpus, rounds, scoring, outcome

As 0228, whose corpus was never run.

- **Corpus:** a third fresh corpus by the literal selection rule. The exclusions add attrs, node-lru-cache and adm-zip.
- **Rounds:** 64, under 22616b57 + F + G + H.
- **Scoring:** the strict bar, as 0228 (including the public-documentation rule).
- **Outcome:** PASS readmits bundle development only. NOT PASS keeps steps 2–5 held, with no automatic re-screen.
- **Screen isolation**, per the owner's "keep C2's isolation":
  - the screen root is `/Users/Shared/devlyn-vr-0228-dev/screen-0229`, inside a C2-owned root;
  - the screen's judge seats run as `_devlynjudge`, with C2's grants, inventory check, process control and credential check;
  - the 0227 driver's permission-toggle `sealed()` is deleted;
  - D2 names the driver change before its Astra SHIP.

## Predictions (before H and any call)

- **"H does nothing" baseline:** at G's observed Codex-primary rate of 1 in 20 on codex-orientation rounds, P(no block in 30) ≈ 0.21. For the 10 claude-orientation replays, P(no block) ≈ 0.9 is a subjective assumption: the Codex pair raised the scenario 0 of 20 times under G, and blocked 1 of 12 in 0227.
- **Root:**
  - R1 0.9, R2 0.5, R3 0.7; gates ≈ 0.3;
  - fresh screen given the gates ≈ 0.5; overall ≈ 0.15.
- **Astra (freeze review, `.devlyn/0229/reg-r1-astra.out.md`):**
  - R1 0.90; R2 given R1 0.45; R3 given the earlier gates 0.65; all gates ≈ 0.26;
  - fresh screen given the gates 0.50; overall ≈ 0.13.

## Principles check

- **#1 No overengineering:** one rubric passage rescoped. One runner change maps the arm to H and fixes the collector, a gap Astra found in 0228's collector. The screen driver change follows the owner's isolation decision. No parser, merge or scorer change.
- **#2 No guesswork:** predicates, orders and predictions fixed before any call. The F control guards against model drift; the baseline is stated.
- **#3 No workaround:** the strict bar stays. Agreement with the base never excuses a requirement the base does not meet.
- **#4–#6:** as 0228.

## Work order

1. Diagnosis and registration PR, after Astra's FREEZE.
2. H: implement, lint, portability suite, identifier grep, Astra SHIP, push. Runner change, Astra SHIP. D1. This is preparation only: nothing is run.
3. **Owner approval** of this plan. No replay, corpus or screen work before it.
4. R1, R2, R3, with Astra reviews and the owner's baseline compares.
5. Corpus. Driver (judge account, D2). Screen, scoring, RESULT.

## Addendum D1 (2026-10-01, before any 0229 replay call)

- **H** = `3afbb18e` on `candidate/0229-fix` (pushed, no PR): one commit on G changing only `verify.md` and its `.agents` mirror. Astra SHIP (`.devlyn/0229/h-r0-astra.out.md`); lint, the portability suite (63 tests, 17 platform skips) and the identifier grep pass (`.devlyn/0229/h-checks.log`).
- **Runner** = [`replay.py`](../experiments/0228/replay.py) and [`collect.py`](../experiments/0228/collect.py) at `17c8b7b8`:
  - arms F and H. `stage <H>` extracts `git archive H config/skills` untrusted into `product-H`; attempts go to `DEV/H/<token>/rep-N` and `DEV/stub-H/…`;
  - G and stub-G stay among the attempt kinds, so 0228's attempts remain closed and inside the judge open check;
  - stub binaries are copied straight from 0227's `dry/` folder. 0228's staged copy in `DEV/stub` was byte-identical and is no longer read;
  - the collector keeps every finding of any rank, INFO included. Its pool holds every rank-2 finding plus every finding on a twin replay; labeling then applies 0228's rule, so the per-seat demotion check sees lower-rank target findings;
  - the guard test is GREEN on this runner (root's run; its fixture setup writes only inside `DEV/scratch`) and RED with the guard disabled (root and Astra). Astra SHIP (`.devlyn/0229/run-r0-astra.out.md`); two Claude reviewers, one on isolation and one on registration fidelity, found no defects.
- **Replay orders** (`replay.py plan`, committed as [`plan-r2.json`](../experiments/0229/plan-r2.json) and [`plan-r3.json`](../experiments/0229/plan-r3.json)):
  - R2, 56 replays in 15 cycles: H on both codex-orientation J4 reference rounds in every cycle (30); H on both claude-orientation rounds in cycles 1, 4, 7, 10 and 13 (10); F on both codex-orientation rounds in cycles 1, 3, …, 15 (16).
  - R3, 100 replays: the other 60 rounds once, then the 20 J2/J3/J4/P2/P3 twin rounds twice.
  - Infra reruns as C1.
- **Nothing of 0229 has run.** R1 starts only after the owner approves.

## Gate results (2026-10-01/02): R1, R2 and R3 pass

- **Owner approval:** relayed by the devlyn-os-v1 session, received 2026-10-01 23:44 KST ("지금 시작"). The judge token account was onedatatech.dev throughout; no swap, no usage-limit event.
- **R1 PASS** (Astra SHIP, `.devlyn/0229/r1-r0-astra.out.md`; record in [`r2/decisions.md`](../experiments/0229/r2/decisions.md)):
  - H staged from `3afbb18e`; its product differs from 0227's only in `verify.md` (55 files);
  - stub 64/64 as the judge, with H's `verify.md` as every seat's rubric frame;
  - probe `probe/05f4b0744c2a/rep-2` passed: the judge opened none of 1,317 hidden paths, and both seats were denied the live transcript, the J4 hidden mechanism and devlyn-cli `.git/HEAD` in their own records;
  - owner compare: changed 0.
- **R2 PASS** ([`r2/`](../experiments/0229/r2/), Astra SHIP `.devlyn/0229/r2-r0-astra.out.md`):
  - 56 replays, 0 infra faults. All 40 H replays are clean references, with no rank-2 finding at all: the Codex primary passed all 30 codex-orientation replays, and the Claude primary returned PASS_WITH_ISSUES on all 10 claude-orientation replays, from rank-1 coverage notes.
  - F carries the diagnosed J4 block in 5 of 16 replays, all from the Codex primary. Root and Astra's blind audit agree on all five labels, with no doubt.
  - Within the session, 0 of 30 H replays versus 5 of 16 F replays on the same codex-orientation rounds (one-sided Fisher p ≈ 0.003). This is consistent with H removing the block, but the gates still cannot show causation (registration limit).
- **R3 PASS** ([`r3/`](../experiments/0229/r3/), Astra review `.devlyn/0229/r3-r0-astra.out.md`):
  - 100 replays, 0 infra faults, 0 excluded reads.
  - All 72 twin replays are twin hits under the strict join: a merge-accepted rank-2 finding that both labelers call a behavioral target match without doubt.
  - All 28 references are clean. Two J2 references ended NEEDS_WORK on Codex coverage findings only, the same missing `allowStale: false`-over-true regression 0227 reported. The predicate counts them clean, and they are reported.
  - **No demotion.** Every seat holding a lower-rank twin finding also held a rank-2 target finding, and neither labeler marks any demotion.
  - Labels: root's drafts (Claude subagents per task, masked inputs only), reviewed by root on every gate-relevant item, and Astra's blind audit agree on every rank-2 label. They differ on 7 rank-1 labels, none gate-relevant; root adopts Astra's.
  - Reported per seat: hits per task are 100% for both engines, except P2 Codex at 1 of 12. Codex's P2 findings name the stale-type cause through collection-to-scalar or scalar-to-collection triggers rather than the recorded attrs-instance trigger, so by 0227's strict precedent they are not matches. Claude hit P2 12 of 12.
  - Reported documentation hit findings: 15 (J3 7, P3 8).
- **Isolation over the whole run:** the owner's baseline compare showed changed 0 after R1, R2 and R3; the same five baseline paths are gone, none removed by the experiment. The judge token appears in 0 of 228,988 files under the 0228 root, and no Codex login copy is left.
- **Against the predictions:** root gave R2 0.5 and R3 0.7, gates ≈ 0.3; Astra gave R2 0.45 and R3 0.65, gates ≈ 0.26. All three gates passed.
- **Next (work order step 5):** a fresh corpus, the screen driver change D2 (judge account), then the 64-round screen under 22616b57 + F + G + H.

## Addendum D2 (2026-10-02, before the screen's freeze): corpus selection and the screen driver

- **Templates:** [`experiments/0229/author/`](../experiments/0229/author/) at `2d51f133`, committed before any author call. They are 0227's with 0228's changes:
  - attrs, node-lru-cache and adm-zip are excluded;
  - PHASE-B drops "run from the repository root" and gains the no-rewrite sentence;
  - the seat runner uses the 0229 workspace root.
- **Selection** ([`selection.json`](../experiments/0229/selection.json)):
  - Phase A (isolated Astra ultra seat) proposed 5 Python and 5 JavaScript candidates. The lowest clone-URL hashes are markdown-it/markdown-it (JS) and dateutil/dateutil (Python); both are eligible.
  - Neither has prior use in `autoresearch/` or `benchmark/`, and neither has agent instruction files.
  - Licenses: MIT (markdown-it); Apache-2.0 per dateutil's LICENSE.
  - Suites:
    - markdown-it passes `npm ci` then `npm test` on host Node v25.4.0.
    - dateutil fails 41 tz tests until its own CI step `updatezinfo.py` generates the zoneinfo tarball (system `zic`; tzdata2024a, pinned by sha512 in `zonefile_metadata.json`). After that step it passes on host Python 3.14.7 (2032 passed). By 0227 B2's precedent (the rule states no provisioning condition), this counts as standard tools.
  - Pins: markdown-it `3c51991c`, dateutil `2642afac`.
- **Toolchains** (inside the screen root):
  - markdown-it: a copy of the official Node v25.4.0 (0227's toolchain copy), with `npm ci` from the pinned lock.
  - dateutil: a Python 3.14.7 venv from `requirements-dev.txt`, plus the lint tools its `.pre-commit-config.yaml` pins (darker 3.0.0 with black and isort>5.9; pre-commit-hooks 6.0.0), and the generated tarball.
  - **Provisioned links**, excluded from Git, kept out of the pristine tars and re-linked on redispatch: `node_modules`, and dateutil's `src/dateutil/zoneinfo/dateutil-zoneinfo.tar.gz`.
  - **Scratch outputs** removed after MECHANICAL: `dist/`; `.hypothesis/`, `.pytest_cache/`, `.tox/`, `.cache/`.
- **Corpus** (private until the result, as in 0227; under the screen root's `private/`):
  - **Requests** (two isolated Astra ultra author seats):
    - dateutil:
      - P1, boundary: recurrence slicing across cache states;
      - P2, ordering: `(tzname, tzoffset)` keys in `tzinfos`;
      - P3, failure state: `gettz` cache-capacity validation;
      - P4, cross-field: ISO week numbers against their week-year.
    - markdown-it:
      - J1, boundary: inline lookahead memoization scoped to the source bound;
      - J2, ordering: `Ruler.moveBefore`;
      - J3, failure state: strict enable/disable batches;
      - J4, cross-field: definition metadata on reference tokens.
  - **Implementation:** eight isolated gpt-6-sol seats.
  - **Calibration** ([`calibrate.py`](../experiments/0229/calibrate.py), model-free and offline, each tree built as the screen builds a round): all eight passed on the first run. Each reference passes every public check and oracle row. Each twin passes the public checks and fails only its designated witness (P1-W, P2-W, P3-W, P4-W, J1-O3, J2-O2, J3-O3, J4-O3). Patch file sets match, and the checks rewrite nothing.
  - **Calibration review:**
    - Astra, per repository, returned REVISE:
      - P1–P4: the darker and `git diff --check` checks compare with `HEAD` and are vacuous once the change is committed;
      - P1: the reference treated slice bounds above `sys.maxsize` differently by cache state, and its oracle crashed on a failed expectation;
      - J1–J4: the specs stated an unevidenced "from the working copy root".
    - Eight Claude checkers, one per task, found no blocking defect. Their minor items were:
      - hints toward the twin in J3, J4 and P3;
      - unrequested reference edits in P2, P4 and J3;
      - P1's step-zero order and oracle coverage;
      - the J3 and J4 mechanism records.
    - Repair 1 covered all of them: two author seats, then implementer seats for P1–P4 and J3.
    - After recalibration, all eight pass and Astra's recheck is SHIP for both repositories (`.devlyn/0229/calib*`).
  - **Seat isolation:**
    - No seat transcript shows a web-search or MCP event.
    - The seats' Codex read scan finds no read of an existing path outside each seat's workspace and the toolchains. Its only outside words are root-relative words from variable-prefixed paths and sed patterns, which name no existing file.
  - **Stub dry runs** (all 64 spans, as the judge) passed twice, with no MECHANICAL retry in either: before the repair (`manifest.dry.json` `5fce4ed6…`), and on the final corpus with the final driver bytes (driver `53abf3cb…`, `manifest.dry.json` `c7c21f0f…`).
- **Driver D2** ([`experiments/0229/screen.py`](../experiments/0229/screen.py), from 0227's):
  - **Bindings:**
    - root `/Users/Shared/devlyn-vr-0228-dev/screen-0229`; `CANDIDATE` = H `3afbb18e`; `CONTRACT` = this file;
    - new `STAMP` and `RUN_ID_PREFIX`; `SCREEN_REPOS` P→dateutil, J→markdown-it; `TOOLCHAINS` with links and scratch outputs;
    - the 0227 pins, read-only; `MECHANICAL_ATTEMPTS` 8.
  - **Deleted:** development mode (`dev_stage` through `g2`, the `DEV_*` constants and their commands), attrs' pyright cache, and the permission-toggle `sealed()`.
  - **Judge processes:** every one runs as `_devlynjudge` (`sudo -n -u … --preserve-env=<names>`) — the seats, prepare's Claude instruction probe and the stub dry run.
    - The environment is the round's, with the judge's own HOME and TMPDIR in its run folder, Git trust for exactly its work tree, and SHELL.
    - The Claude token is read at launch and passed only as `CLAUDE_CODE_OAUTH_TOKEN`.
  - **Isolation:**
    - The driver's umask is 077.
    - `isolate()` runs before prepare's rounds and in the open check before run and redispatch. It makes the root owner-only with judge search; `product` and `bin` are readable through their modes, with the pinned binaries executable by the judge.
    - `rounds/`, `homes/`, `dry/` and `toolchains/` are search-only. Every round, home and dry entry is closed, every toolchain is denied, and every other entry is closed. No Codex login copy may remain.
  - **Per run:**
    - The judge gets inheritable read/write without `delete` on its work tree, its judge HOME and TMPDIR, and its round's Codex home; search on the round folder; and its toolchain undenied. The Codex login is copied in.
    - Afterwards, in this order:
      1. judge processes stop: TERM, then KILL with bounded waits, by uid, with the OS-agent exemption;
      2. the toolchain is denied and the folders closed, even if stopping fails;
      3. the login copy is deleted through `owned()`, and a missing copy fails closed;
      4. every entry must be a folder, an owner-readable regular file without the judge token and not a login copy, an expected provisioned link, or a terminated Codex's arg0 dispatch link to the pinned binary.
    - Only then does the driver write its records, by exclusive no-follow creation, in the round folder where the judge had search only. A round that fails the check is classified without reading any judge-written file, and scoring treats it the same way (`unread_facts`, which fails condition 5).
  - **Transcripts** are copied from the judge HOME to `transcripts/<tok>/attempt-N`. Nothing is moved out of the owner's HOME anymore.
  - **Account drift:** Codex is checked by its account id, as in 0227. Claude is checked by the judge token file's identity (device, inode, size, mtime). The owner swaps the token by replacing the file; its bytes are never read for this.
  - **`inventory LABEL`** is a read-only marker scan over HOME except Library, `/Users/Shared`, `/private/tmp` and `$TMPDIR`. The markers are the root's name and one line per hidden mechanism.
  - **Open check:** `prepare --inventory`, `run --pr N --inventory` and `redispatch --inventory` each need an inventory under 30 minutes old. In each, the judge must fail to list or open every hidden path.
  - **Observed, not changed:** the judge's per-uid Claude folder `/private/tmp/claude-450` holds only prompt-cache diagnostic hashes, with no task content.
  - **Self-test:** 0227's cases plus the D2 cases, among them a check that no top-level function is defined twice. Review caught two such redefinitions, `check` and `inventory`.
  - **Smoke test:** with real `sudo`, a judge run in a grant could write its outputs and HOME. It could not open a sibling round, the private corpus or `~/.zshrc`, and nothing remained afterwards.
  - **Review** (`.devlyn/0229/d2-r*`): Astra R0 REVISE (5) and two Claude reviewers (1 critical, plus HIGH/MEDIUM/LOW findings), all adopted; R1 REVISE (1); R2 SHIP.
