# 0227 — fix the two 0226 BLOCKED causes, then re-screen the scripted VERIFY on fresh tasks

2026-09-29. **Status: REGISTERED, frozen before the fix commit, any probe call and any corpus authoring.** Design: fact brief; independent R0s (root, from three angle drafts with cross-lens critiques; Astra gpt-6-astra/ultra, read-only); R1 left two points open: root adopted Astra's G3 correction (the unchanged 0226 J specs still require "offline", so a truthful BLOCKED must be allowed there, `.devlyn/0227/r1-astra.out.md:23`), and the retry question went to the user. **User decisions (2026-09-29):** fix both causes and re-screen on fresh tasks ("1번으로 진행해줘"); pre-freeze probe calls on already-public 0226 material are allowed, six Claude calls and a 64-round rehearsal ("예, 시험해도 됨"); the strict bar with the execution-condition strengthening below ("완벽 기준 + 강화"); a Claude CLI corrective re-ask inside one seat invocation is recorded and is not a retry ("기록만 하고 통과 인정"; Astra recommended counting it as a failure); root merges 0227 research PRs after Astra SHIP, and a NOT PASS ends automatic re-screening ("둘 다 예"). Raw record: `.devlyn/0227/`.

## Why this iter exists

- **Pre-flight 0:** this iter exists because it targets a user-visible failure found by [0226](0226-verify-recall-screen.md) — correct code ending BLOCKED in 5 of 32 reference rounds ([RESULT](../experiments/0226/RESULT.md)) — and unblocks the go/no-go decision on the held step 2 of [0225](0225-resolve-cost-cuts.md).
- **#7 Mission-bound:** it serves Mission 1 because the scripted VERIFY decides whether full resolve keeps its verification quality at lower time and token cost, and a verifier that blocks correct code is a single-task reliability failure.

0226 ended NOT PASS on condition 5 only: 32/32 target hits, 0 false alarms, 0 unsupported extras, 0 invalid references. Its five BLOCKED reference rounds had two causes (`.devlyn/0227/brief.md`):
1. **Claude emission.** Three Claude seats wrote prose before their JSONL. The candidate's prompt promises that leading text is ignored (`verify.md:131`), but its parser skips only plain lines (`judge-output-parser.py:17-18,64-66`), so the merge rejected the seats. One of them also has an invalid JSON escape, which no parser rule can accept without rewriting model bytes.
2. **Judge BLOCKED on an unevidenced condition.** Three Codex primaries chose BLOCKED because the specs demanded `npm test` "offline, with Node 22" and the sealed MECHANICAL record shows neither, following `verify.md:36-38`. The objection was true: root's authoring prompts added those lines, MECHANICAL ran without a network sandbox, and the product's spec template requires conditions to be carried by the verification commands (`devlyn:ideate/references/spec-template.md:86,99`).

**0227 decides one thing:** whether the fixed candidate may re-enter development of the steps 2–5 bundle. Besides 0226's limits (0226 "Why"), it cannot establish behavior on specs that state conditions nothing can evidence (its corpus states none), nor how the new `verify.md` sentence changes judging of such conditions, nor whether judges raise more coverage-only NEEDS_WORK on correct code (reported below, no effect).

## Candidate

- **One fix commit F on `22616b57`,** on a pushed branch with no PR, not merged during 0227 (main stays at step 1). Addendum B1 names F before any probe call; nothing in F changes after B1.
- **Cause 1 — Claude seats emit through the CLI's structured output.** Claude seats add `--json-schema` with a frozen schema: `findings`, each with the fields `verify.md:131` lists, types matching all 130 accepted 0226 Claude findings (severity `CRITICAL`/`HIGH`/`MEDIUM`/`LOW`/`INFO`, string `confidence`, optional boolean `verdict_binding` on any severity), and `verdict` in `PASS`, `PASS_WITH_ISSUES`, `NEEDS_WORK`, `BLOCKED`. One validator and one render function in `judge-role-evidence.py` serve both Claude authentication and the timed-out Claude path (`verify-merge-findings.py:467-472`): the envelope must have subtype `success`, `is_error` false, a session id and a `structured_output` object that validates; `stop_reason` and `result` are recorded, not required. The render writes the canonical `.stdout` (one JSON object per finding, then the verdict line), and the existing parser and merge run unchanged. Anything else, including `error_max_structured_output_retries`, is malformed output (seat BLOCKED, as today). `claude.md`'s projected "Output discipline" section gains one sentence: in a VERIFY judge seat started with a JSON schema, return the findings and verdict only through the structured-output tool. Codex transport is unchanged (64/64 accepted in 0226). No parser widening, no escape rewriting, no harness re-ask.
- **Cause 2 — one rubric sentence.** `verify.md:37-38` becomes: "If a spec axis remains uncovered, emit a verdict-binding coverage finding instead of continuing or assuming PASS. Use `BLOCKED` only when evidence essential to judging a mandatory condition is unavailable and no change within the authorized surface could produce it." Seat verdict authority (`verify-merge-findings.py:479`) is unchanged, so an honest BLOCKED stays possible and an unevidenceable condition is not sent into repair.
- **One subtraction.** The unkept promise at `verify.md:131` goes: "Text before the first record is ignored, carries no finding or verdict, and cannot precede `PASS`; after it, the harness rejects any non-record line" becomes "After the first record, the harness rejects any non-record line". The linted sentence "Both seats emit only JSONL findings" stays.
- **Obligations:** touched self-tests updated; the lint needle at `lint-skills.sh:1280` becomes `verdict-binding coverage finding`; `scripts/lint-skills.sh` passes (it runs the frozen r-weld collector negatives unchanged); every change is mirrored byte for byte into `.agents/skills`. Root implements; Astra reviews `git diff 22616b57 F` until SHIP.

## Gates before authoring (development evidence; never a 0226 regrade)

Expectations are frozen here. G2 and G3 rounds are built by the 0227 driver's development mode from `experiments/0226/corpus`, exactly as `prepare` builds rounds (MECHANICAL included), in a development root. "Merged verdict" means the verdict the merge derives; "seat verdict" means the worse of a seat's finding ranks and its terminal verdict, as the merge derives it (`verify-merge-findings.py:479`). Root labels target-mechanism matches against each task's `hidden/mechanism.md`, and Astra audits them. Infra faults follow "Faults" below; any other gate failure stops the work: root records it and reports to the user, no route is switched silently, and a revised route needs the user's decision.
- **G1 (model-free, before Astra's SHIP of F).** All 61 accepted 0226 Claude outputs convert to objects that validate against the frozen schema and round-trip parse → object → render → parse with identical findings and verdict; fixtures with backticks, backslashes, quotes, newlines and non-ASCII come back byte-exact; envelope negatives reject (non-success subtypes including `error_max_structured_output_retries`, missing or non-object `structured_output`, truncated JSON, duplicate keys, missing fields, unknown verdict, a verdict-binding finding with `PASS`); the three rejected 0226 Claude outputs stay rejected on the text path; lint and every touched self-test pass.
- **G2 (live; 6 calls: each Claude role on three spans; only the Claude seat is invoked, with the exact seat argv).** The J2 reference (the span behind 0da1288ee3b9, a LOW-with-backticks reference), the C1 reference and the C1 twin, with condition-aligned development copies of both specs committed in B1: each spec's execution-condition line ("offline, with Node 22"; "offline, with PYTHONPATH=src in the supplied Python 3.13 environment") is replaced by version-check verification commands (`node --version` with `stdout_contains` `v22.`; `python --version` with `3.13.`) and, for C1, `PYTHONPATH=src` inside the test command. Each call: subtype `success` with a valid `structured_output`; at least one Read or Grep call (Glob and the structured-output tool do not count); on the references the seat verdict is PASS or PASS_WITH_ISSUES with no rank-2 behavioral finding, on the twin it is NEEDS_WORK with the seat's own rank-2 finding of the target mechanism; any corrective re-ask is identified in the retained transcript, else recorded as UNKNOWN.
- **G3 (live; the 64 exposed 0226 spans with unchanged specs, F).** All 128 seats authenticated and accepted (0 emission, authentication or transport failures); every Claude seat makes at least one Read or Grep call; in every twin round each seat has a retained rank-2 finding of the target mechanism; a BLOCKED is allowed only where Astra confirms that the seat's rank-2 findings are all execution-condition findings about a condition the span's spec states and MECHANICAL does not evidence; any other BLOCKED fails the gate. Re-asks are reported. The development root is deleted once its record is kept (16 GiB free).

## Corpus

As 0226 ("Corpus"), with these changes:
- **Repositories:** "never used" now also excludes tkem/cachetools and hapijs/joi; the author lists fresh candidates.
- **Author and implementer isolation:** each runs in a fresh Astra ultra (author) or gpt-6-sol (implementer) session under `env -i` with its own fresh `CODEX_HOME` (as 0226's `run-author.sh`), with web search and apps/connectors disabled. Work counts only if its transcript shows no web-search or MCP tool event and the seat read scan finds no read outside its workspace and toolchains.
- **Instructions:** B1 commits the author and implementer prompt templates before any probe: 0226's prompts made repository-neutral (the author derives the verification commands from the pinned repository's own configuration), without the phrases "offline", "with Node 22" and "with PYTHONPATH=src in the supplied Python 3.13 environment", and with one added rule: an execution condition appears only as a declared verification command whose sealed output evidences it (a runtime version check with `stdout_contains`, or an environment assignment inside the command); a condition nothing can evidence is not stated. They are filled mechanically after selection and carry no hint of 0226's results.
- **Calibration** uses the screen's own toolchains; every verification command, version checks included, passes on reference and twin.

## Rounds, apparatus, seal, freeze and witness

As 0226 ("Rounds", "Apparatus and seal", "Freeze and witness"), with the candidate replaced by F. All changes are in a copy, `autoresearch/experiments/0227/screen.py` (0226's driver stays byte-identical):
- a new sealed root `/Users/Shared/devlyn-vr-0227`; durable copies of the pinned Claude bytes and models cache outside `$HOME` and outside both roots; a development mode (its own root, the 0226 corpus, no witness) for G2/G3;
- a heartbeat line no longer splits a Codex exec block, and an unparsed block ends at the next `exec`; slash-free regex or glob words are not read candidates; each ambiguous read records its origin (0226's RESULT had to correct a misattribution);
- scoring gains the execution-condition kind (no check, neutral per finding, outside the reference-round exemption); a candidate API incompatibility fails `prepare` loudly, while a genuine seat rejection stays condition-5 evidence; stubs are schema-aware; `prepare`'s instruction probe drops `--json-schema`;
- identified Claude re-asks are recorded per seat (else UNKNOWN); the driver and verifiers write no bytecode.
A stub dry run of all 64 spans through rendering, authentication, merge and scoring precedes each Astra SHIP of the driver (development mode before B1; fresh-corpus bindings before the freeze).

## Scoring (pre-committed)

As 0226 ("Scoring"), with:
- **Execution-condition finding:** a finding about the runtime or environment of the verification commands (runtime or toolchain version or identity, environment variables, working directory, network), whether or not the spec states the condition. A finding that also makes another claim is labeled by that other claim; a doubtful case is an execution-condition finding. It is never a hit.
- **Unsupported terminal (strengthened, user decision):** a reference round whose merged verdict is NEEDS_WORK is a false alarm unless it carries a rank-2 finding that is pre-existing, an invalid reference, or a coverage finding that is not an execution-condition finding. On twin rounds execution-condition findings are reported and have no effect. Reference rounds ending NEEDS_WORK with coverage findings only are counted and reported.

## Registered outcome (strict bar)

**PASS** iff all six 0226 conditions hold, with condition 2 using the strengthened unsupported terminal and condition 5 reading "no retry" per the user's decision: a Claude CLI corrective structured-output re-ask inside one seat invocation is part of that invocation, every identified re-ask is reported (else UNKNOWN), and 0227 does not claim retry-free emission. Anything else is **NOT PASS**, reported with every violated condition and the classification of every event.
- **PASS:** as 0226, for the fixed candidate (22616b57 + F).
- **NOT PASS:** steps 2–5 stay held. No automatic fix-and-rescreen: another registration needs a materially new diagnosis and the user's decision.

## Faults

As 0226 ("Faults" and Addendum A1; A1's envelope fields now also carry Claude structured-output errors). The sealed three-attempt MECHANICAL retry during `prepare` belongs to the apparatus, before any seat runs.

## Predictions (before the fix and any probe)

- **Root:** 32/32 hits (P ≈ 0.8); 0 false alarms, unsupported extras and invalid references (P ≈ 0.7); 0 rejected Claude outputs (P ≈ 0.85); 0 merged BLOCKED; median round wall ≤ 40 s; P(PASS) ≈ 0.4.
- **Astra:** 32/32 hits; 0 false alarms, unsupported extras and invalid references; 128/128 seats accepted; 0 BLOCKED, retries or execution-only repairs; median round wall ≤ 60 s; P(PASS) = 0.5.

## Principles check

- **0 Pre-flight:** ✅ see "Why this iter exists".
- **#7 Mission-bound:** ✅ see "Why this iter exists".
- **#1 No overengineering:** ✅ the product change is one transport switch for Claude seats, one replaced sentence and one deletion; parser widening, runtime records and offline enforcement were rejected.
- **#2 No guesswork:** ✅ gate expectations and predictions are fixed before any call; G2/G3 test the structured channel before fresh material is spent.
- **#3 No workaround:** ✅ invalid escapes are not rewritten, truthful evidence gaps are not downgraded, and the corpus follows the product's own alignment rule.
- **#4 Worldclass production-ready:** ✅ the strict bar and the one-shot join are kept.
- **#5 Best practice:** ✅ emission validity comes from the CLI's own schema channel, not a hand-rolled recovery heuristic.
- **#6 Layer-cost-justified:** ✅ VERIFY stays a pair with no new layer; predicted median round wall ≤ 40–60 s (0226: 26 s).

## Work order

1. This registration: Astra FREEZE, PR, root merges.
2. Fix commit F: implementation, G1, Astra SHIP, pushed branch.
3. Driver copy with the registered changes and development mode, stub dry run, Astra SHIP. Addendum B1 names F and the driver commit and commits the G2 spec copies and the author/implementer templates.
4. G2, then G3; Astra reviews both.
5. Corpus: repository selection, blind authoring, implementation, calibration, calibration review.
6. Driver bindings for the fresh corpus, stub dry run, Astra SHIP; freeze commit and witness, 64 rounds, masked scoring with Astra audit, join, RESULT.

## Addendum B1 (2026-09-29, before any probe call)

- **Fix commit F = `f40da73b`** on `candidate/0227-fix` (pushed, no PR, parent `22616b57`). Astra review: REVISE (3: the timed-out Claude path skipped the envelope check; U+0085/U+2028/U+2029 split a rendered record under the parser's `splitlines`; the portability test's Claude argv lacked the schema) → SHIP (`.devlyn/0227/fix-r*`). G1 passed (`autoresearch/experiments/0227/g1.py`, `.devlyn/0227/g1.log`: 61 accepted 0226 Claude outputs round-trip, the 3 rejected stay rejected, fixtures byte-exact, envelope negatives reject); `scripts/lint-skills.sh` and the portability suite pass. Two lines in `claude.md`'s "Invocation" section, which judge prompts do not include, document the new flag.
- **Driver** `autoresearch/experiments/0227/screen.py` (this commit), with the registered changes. Task ids and toolchains come from one `REPOS`/`TOOLCHAINS` table, which the fresh-corpus bindings rebind. Development mode: `dev-stage` copies 0226's committed corpus (its digests must equal 0226's manifest), pinned clones and toolchains, relocating venv console-script shebangs; `dev-dry` is the model-free stub dry run of all 64 spans; `dev-prepare`, `dev-run` and `dev-report` produce G3 in `/Users/Shared/devlyn-vr-0227-dev` (`prepare` keeps its 64 Claude instruction probes); `g2` runs in `/Users/Shared/devlyn-vr-0227-g2` with the candidate's stub as the Codex seat, and each Claude seat's verdict is the merge's `source_verdicts` entry for that seat. An identified re-ask is a CLI meta user turn containing "tool to complete this request. Call this tool now." (Claude Code 2.1.281). Replayed over 0226's Codex transcripts, the read-scan changes leave 0 of its 12 ambiguous reads.
- **G2 spec copies:** `autoresearch/experiments/0227/g2-specs/{C1,J2}/`.
- **Author and implementer templates:** `autoresearch/experiments/0227/author/` — `CORPUS-RULE.md`, `PHASE-A.md`, `PHASE-B.md`, `PHASE-C.md` and `run-seat.sh` (pinned codex-cli 0.156.1 under `env -i` with a fresh `CODEX_HOME`, `web_search="disabled"`, and apps, plugins, remote plugins, sub-agents, browser and computer use disabled). The author workspace also receives F's `spec-template.md` and `expected.schema.json`, as in 0226.
- **Pins:** `/Users/Shared/devlyn-pins-0227` holds Claude Code 2.1.281 (`a922981f…`) and the models cache (`b7105827…`), 0226's digests.

## Registration review

Astra (gpt-6-astra, ultra, read-only), in parallel with three Claude critics (gaming, executability, subtractive): R0 REVISE (Astra 1: gates must require real source inspection; the critics added the development-mode driver before the gates, the stated envelope check and frozen schema, B1-frozen author templates and G2 spans, author isolation, the subject-defined execution-condition kind, exact replacement texts, scoring code and several deletions) → R1 REVISE (1: G2 cannot use a merged verdict with only Claude seats called) → R2 FREEZE. Root dropped three uncited additions (a separate seat-BLOCKED check, which Astra withdrew with evidence; turn counts; a `result`-text report). Raw: `.devlyn/0227/reg-*`.
