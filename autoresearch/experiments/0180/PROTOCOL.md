# 0180 — fresh direct A/B development screen

This completes the next admission step of0179 and makes its go/no-go decision
concrete: retain the minimal contract as a confirmation candidate only if it
improves complete-task success without a paired regression. It serves Mission1
single-task quality; it does not establish superiority, replace current customer
instructions or activate the later independent-review/repair treatment.

## Inputs and admission

Two newly authored, synthetic development tasks: `small/request.md` fixes an
ordered selection parser; `hard/request.md` fixes a durable event inbox API/CLI.
Both have stdlib-only seeds, preserved legacy tests and an attribution file.
These are mechanism-oriented cases, not a representative real-project sample.
The task prompts are the full user inputs. No calibration or oracle files enter
participant trees. The sole tree difference is B's committed AGENTS.md, copied
byte-for-byte from0179; A has no project instructions. Both use neutrally named fresh Git roots outside the research repository and instruction-bearing
ancestors. The first workspace-write probe exposed tool-read contamination despite
render parity; its failure is retained, and the corrected location is requalified.

Admission requires both valid implementation variants per case to pass, both
seeds and every declared defect mutation to fail, unchanged legacy tests to pass
on valid implementations, independent Fable/Grok advice adjudicated, and actual
A/B workspace-write edit/test probes to pass. All raw failures stay recorded.
Valid alternatives use regex versus token parsing, and implicit SQLite context
transactions versus explicit transaction control with eager iterable capture.
The hard alternatives share validation and CLI code; this checks freedom in
transaction strategy, not independent coverage of every implementation axis.
The oracle compares observable contracts, not source shape. Root wrote these
cases/references/checks, so their independence is procedural, not independent
authorship; advisors inspect that possible shared blind spot before freeze.

No problem-domain changes, instruction tuning, oracle edits or retries after
the first quality dispatch. A discovered apparatus defect invalidates affected
results and gets a separate documented decision; never retroactively regrade.

## Frozen execution

- Codex CLI0.154.0; requested model `gpt-6-astra`, reasoning effort `high`, native built-in
  instructions retained. Process-local empty native config, opaque native auth
  copy, fixed model cache, external skill cards disabled, apps/plugins/hooks/
  multi-agent/skill-search disabled, web disabled; `workspace-write`, ephemeral,
  no config/rules inheritance. Identical tools/settings/permissions per arm.
- Use `.devlyn/0180/launch.py`; full argv, CLI version, normalized role/type/text
  render, prompt, baseline file hashes, raw events, stderr, diff and result are
  retained for each draw. The launcher and dependencies are digest-bound in the
  pre-dispatch manifest. Native request capture and OS-enforced read isolation
  are not available; renderer parity and command evidence narrow that limitation.
  The render entrypoint omits exec-only ignore-config/rules/ephemeral flags;
  empty process-local config narrows, but does not erase, that evidence gap.
  The server-side resolved model/version is not independently attested. Native
  startup may log malformed external skill discovery, despite zero rendered cards.
- All draws serial, fresh process/config/tree, no resumed context. Order:
  `small-1-A`, `small-1-B`, `hard-1-B`, `hard-1-A`, `small-2-B`, `small-2-A`,
  `hard-2-A`, `hard-2-B`. Two draws per arm per task; small ABBA, hard BAAB.
- Small:300 seconds; hard:600 seconds wall time per native process, including
  its tools and in-session repairs. Wrapper enforces timeout. Native token/output
  limits remain identical defaults; no operator token stop. No extra attempts
  or silent model substitution. A concrete block/unanswered material question,
  timeout or runtime failure remains an incomplete draw with consumed time.
- No operator feedback or hidden-check results during draws. Run external
  assessment after all eight outputs are sealed. Qualification probes use a
  different trivial task and120 seconds; never count them as quality samples.

## Assessment and decision

Primary success requires every explicit requirement, preserved tests/NOTICE,
legacy behavior, requested scope and no unresolved HIGH/CRITICAL source finding.
`score.py` records black-box contract/legacy outcomes; participant-authored tests
and their execution are reported separately, with no product-quality bonus.
Passing mechanical checks or native exit0 alone is insufficient. Instruction
preservation, no commits/publication and no outside-assessment access are audited
separately; a treatment-contaminated draw is not usable success evidence.

After execution, source review packets contain task, seed, final source and
checker outcomes, with labels/model/timing/AGENTS stripped. Native Fable5.1 and
Grok4.6 inspect independently; root is unblinded and adjudicates concrete
counterexamples. No repairs to frozen participant products. A missed requirement
outside the frozen oracle is a failure, supported by a retained counterexample;
do not change the oracle or count a newly weakened domain as a pass.

Report all draws and requirement misses, infrastructure failures and unavailable
telemetry. Compare times only among matched complete products, retaining failure
time in the full table. Report native elapsed time and independent assessment
separately; verification time is native time plus measured external assessment,
not inactive conversation time. Use observed token usage; costs UNKNOWN unless
actually reported. Preparation/advice overhead stays separate.

Pairing is by task and repetition index: small-1 A/B, small-2 A/B, hard-1 A/B,
hard-2 A/B. A quality lift requires all eight draws valid, B’s total success
count strictly greater than A’s, and no pair where A succeeds and B fails.
A valid timeout is an incomplete product (failure for the success count); an
infrastructure error or contaminated treatment makes the screen INCOMPLETE
and ineligible for a lift claim. Tied total success means NO_LIFT even if timings
differ. Native process exit alone never resolves product status.

Prediction: B improves complete-task success with no paired regression. A tie,
regression or incomplete evidence means no quality-lift claim or promotion. A
positive development result permits disjoint repeated confirmation only. Eight
draws do not establish equivalence or general model quality. Without a current
installed-contract arm, this cannot justify replacing the shipped instructions.

Subtractive-first: no production changes, router or new framework. Task seeds,
observable checks, distinct valid alternatives and isolated mutations are the
minimum evidence for admission after0177's invalid fixture and0179's contamination.
Removing calibration or context parity would reopen those measured failures.
