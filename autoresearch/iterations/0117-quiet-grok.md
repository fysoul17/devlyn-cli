# 0117 / A16 — versioned Grok quiet-process correction

2026-09-06 — **IMPLEMENTED/REFROZEN; full gates and final review pending; collection NOT LAUNCHED.**
Owner: [0117 spec](../../docs/specs/0117-quiet-grok/spec.md), run `rs-20260905T150205Z-fbdcf616cd7f`.

Pre-flight 0: prevents collection from treating an observed active Grok seat as quiet.
Mission 1 (#7): repairs the quiet-account prerequisite for the unmeasured layer-lift decision.
Why-chain: both gates appeared quiet because their Grok alternative required the plain basename
and `-p`; the violated invariant is recognition of the attested supported CLI invocation.

**Before prediction:** the absolute-path versioned Grok `--prompt-file` invocation incorrectly
appears quiet in both predicates. [Corrected root red](../../.devlyn/0117/red-v2.json) binds sealed
argv and owned process rows: drain `[]`, runner `[true, "quiet"]`; option-only also misses.
[Original red](../../.devlyn/0117/red.json) is preserved unchanged: its `observed_form` label was
incorrect and proves only a plain-shim replay. The historical 0114 audit established the
separate active-root-state block only; usage/window were not evaluated, with no overall gate PASS.

**Focused actual results:** `python3 .devlyn/0117/focused-check.py <stage>` executed only the
existing gate-predicate/writer-state assertion blocks plus injected process replays:
[baseline](../../.devlyn/0117/focused-baseline.json) exit 0 (old assertions pass, regression replays fail);
[red](../../.devlyn/0117/focused-red.json) exit 1 (both extended blocks fail before the regex fix);
[green](../../.devlyn/0117/focused-green.json) and [round0 final](../../.devlyn/0117/focused-final.json)
exit 0 (both blocks and all 10 command/state replays pass). This predates the R1 pin-only
refreeze and is not current pinned-byte proof. The attested binary row comes from
`red-v2.json`; no live process scan or model invocation was used. Versioned/plain long option and
legacy `-p` block with root absent/completed PASS; quiet/unrelated basename pass. Existing
active-root-state and archived-state controls remain. [Scope/deletion evidence](../../.devlyn/0117/scope-and-deletion.json)
retains all 27 drain + 75 runner assertions; tests add one parameterized assertion in each seam.

### A16 registration

Final code/tests/README → existing runner `normalized_apparatus_sha256`
→ only `params.apparatus_sha256` → both parameter pins → exactly seven existing seals.
[R1 refreeze receipt](../../.devlyn/0117/refreeze-r1.json) and
[implementation evidence](../../.devlyn/0117/implement-evidence-r1.json) close both root LOW findings:
the audit identified the missed execution; the registered README delegates mutable status to HANDOFF.
[Round0 refreeze](../../.devlyn/0117/refreeze.json) remains historical evidence. Current hashes:

- Runner: `643712f2ab487ff3264ba15b7b03660df64384dd9325e5fa8aa61b804fcba525`
- Apparatus: `295f7d9b7ad70e1d31420ab868dd2c15264c19e980867f04bf0b26201d0fe7e6`
- Params: `f339e7629683303aa8ae94c4770f6231cdf150c8bbebff626d2970d4e2970f3c`
- Product staged digest unchanged: `ee8f74d4d2a5061c36b1ad2b4459f6801f08af3b0d08d069a756532bdb8a89f1`

Drain stays unsealed. Model/version/effort seats, corpus/panel, 4/1/1 reps, thresholds,
arithmetic, deadlines and usage/window policy are unchanged. Historical A1–A15 hashes,
[0114 scope/caveat](0114-harness-direction.md#checkpoint), prior outputs and pre-A15
noncomparability remain; installed original runtime is fixed, 0115/0116 candidates unadopted.
Fresh reservation only: `~/.local/share/nx01/iter0113/quick-a16-1` / `lift-quick-a16-1` (absent).

Root owns full gates, fresh actual Codex/Fable 5.1/Grok 4.6 final review, implementation commit,
and the separate final status checkpoint. Only afterward may root launch the existing quiet-gated
drain: quiet account, usage ≤10%, no other CLI seats, outside 23:00–01:00 KST, actual-pair smoke,
one lane, 72 base cells, infra-only attempts 2/3, one evaluation and exact `NEEDS_TOPUP`.
No smoke/panel/scoring ran during IMPLEMENT; no runtime lift or whole-harness readiness is claimed.

Principles #1/#3/#5 (No overengineering / No workaround / Best practice): replace only the two
Grok subpatterns; reuse injection seams. Final deletion attempts removed the version suffix or
long-option alternative in memory: each restored drain `[]` and runner `[true, "quiet"]` on the
attested row. Remaining test additions prevent recurrence and bound the basename/state behavior;
R3 requires registration/status evidence. Repeated launch-policy prose was deleted from the A16
stub in favor of its existing policy. #2 (No guesswork): raw red/green above; #4 (Worldclass
production-ready): final gates/review pending; #6 (Optimized): focused deterministic checks only.
