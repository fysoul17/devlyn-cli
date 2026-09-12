# 0151 — Explicit pure-design generated verification

2026-09-12. Baseline `f50ce5b9c269fc8aa8aea7ace7a5042e8aafbb72`.
Root implements directly without resolve; native Fable 5.1 and Grok 4.6 provide
independent read-only design advice and source review. Prospective completion
receipt: `8f5f5ba32515beadb1f4ed47`.

## Why this iteration exists

Pre-flight 0: close a user-visible contradiction: generated authoring permitted
an empty pure-design Verification section that the checker rejected. Mission 1
gate 1: preserve explicit intent without vacuous empty-contract success.

The prediction was written before reproduction. On baseline, both the documented
empty section and an explicit inline `pure_design` declaration fail authoring
with exit 2 and runtime with exit 1. Existing sibling pure-design succeeds.
Why does the declaration fail? Inline validation admits only executable commands.
Why is a validator-only relaxation insufficient? Staging absence also means
missing contract to generated runtime, and its no-file return skips probes and
fresh results. Contract presence must be independent of command staging.

## Bounded repair and decision

Inline accepts the existing `pure_design` concept only with an explicit empty
`verification_commands` list. Unmarked/false empty lists, missing lists,
nonboolean flags, contradictory commands, malformed JSON and unsupported fields
still reject. `pure_design: false` with executable commands is a valid redundant
declaration; generated and legacy inline paths share the grammar.

`stage_from_source` now distinguishes `(found, staged, error)`, matching sibling
presence semantics. Pure design removes stale staging. Runtime follows the
existing zero-command probe/result/scope path. The staged-file nonempty-command
schema, benchmark-prestaged precedence and real-spec sibling checks stay intact.
Bootstrap, self-tests and the native portability caller consume the new tuple.
Generated source type and digest behavior stay intact for existing source files.

Both independent design reviewers selected explicit inline declaration with the
existing no-file path. Root rejected the preliminary full-object staging option
because it would change the canonical staged schema and require origin-selected
validation. Active inspection showed the process-evidence reader itself accepts
empty lists; that narrower concern was not the decision's basis. No shared
consistency abstraction was added: sibling lists may be omitted, inline lists
must be explicit. Authoring now gives the exact declaration and retains semantic
source-review obligations; a declaration does not prove pure-design correctness.

## Verification

Twenty-one baseline and twenty-one final real-CLI controls retain raw outcomes.
Every final expected outcome matches. Explicit generated/legacy pure design and
false-plus-executable become valid; malformed cases remain rejected. Existing
executable/sibling controls retain behavior. No stale command executes. Valid pure
design produces `commands: []`, null process evidence and no staged command file.
Digest mismatch still fails at runtime; missing mandatory probes fail on probe
integrity after valid authoring. No broad semantic-recall or speed claim follows.

The checker self-test adds nine inline cases, absent/present benchmark staging,
and missing/valid probe controls. A valid supplementary probe produces exactly
one verified process result. Bootstrap self-test adds pure inline integration.
Both self-tests pass. An actual UTF-8-disabled portability smoke first failed on
the old two-tuple assertion, then passed after its one-line expectation update.
This local smoke ran on Darwin; native Windows remains a delivery CI gate.

A registered subtraction control restores the old no-file guard: missing required
probes falsely return 0 and valid pure design produces no fresh results. The
retained first attempt was invalid apparatus (missing colocated platform helper);
the unchanged mutation was accepted only after supplying that exact helper.
A separate Git/base-bound scope control passes an allowed edit and rejects an
outside-surface edit with exactly `scope.out-of-scope-file`.

First full lint: FAIL, 628.659s. Initial `.claude` mirror parity and a structural
check's old local-variable names failed. Current exact mirror parity is verified;
the intervening refresh actor was not established. Update the one obsolete lint
binding string; preserve the failure. Final full lint passes in **333.137s** on
unchanged final bytes. Main source and final tiny-delta reviews both complete:
Fable **PASS_WITH_ISSUES**, Grok **PASS**, with exact native model identities,
zero tool calls and no established CRITICAL/HIGH in the scoped repair. Root
accepts the scoped source. Hosted CI and delivery remain separate receipt gates.

## Limits and next frontier

Retained LOW advice concerns deeper required-probe/tag coverage. A valid digest
with an absent probe file is impossible under the actual digest reader; direct
stale-command controls cover deletion independently of bootstrap integration.
The executable-authoring wording was shortened by removing “only”, preserving
accepted redundant `pure_design: false` without adding another option.

A missing generated source file remains a separate pre-existing gate no-op:
baseline and candidate both return 0 without results when the bound file vanishes.
This is an isolated checker observation, not a demonstrated full-pipeline false
PASS. Inspect that next, separately from benchmark-prestaged oracle validation.
Frozen 0140/0147 comparisons, A16 and all four broad research priorities retain
their boundaries. No npm release or comparative superiority claim.

No workaround / Production ready: preserve declaration, missing-contract and
mandatory-probe distinctions. No overengineering / Best practice: reuse the
existing zero-command representation and standard unlink; no new staged format.
No guesswork / Worldclass: prospective predictions, actual counterexamples,
full gates and independent exact native identities. Optimized: remove the
redundant staging-dependent guard, without claiming measured whole-run savings.
Evidence lives in `.devlyn/0151/`, frozen as `.devlyn/0151-evidence.tar.gz`;
canonical source hashes and both installed skill mirrors are bound in
`final-source-manifest.json`. The native driver is repository test tooling, not
an installed skill; delivery CI binds its separately uploaded bytes. Delivery
and cleanup remain receipt-owned.
