# iter-0095 — PLAN delivery byte-fidelity (STUB, not yet registered)

Successor to iter-0094 (DECISIONS 0094.1), which ran the R5 re-gate matrix
past controls for the first time and closed NO SHIP CREDIT on exactly one
failure: candidate-discovery delivered the rendered PLAN prompt minus its
single terminal LF (10,015 vs 10,016 bytes; sha `c9d8a32e…` vs
`daf10207…`). R1 (native foreground PLAN dispatch, landed `83b275e`,
formally verified green) is NOT refuted — candidate-simple delivered
byte-exact with a perfect call shape in the same matrix, and candidate arms
were faster (0.866× summed). Live delivery credit is still the only thing
owed. Nothing here is frozen — a fresh registration round (3-seat FREEZE +
Terra instrument proofs) must freeze all of it before any arm runs.

## Design round already held (2026-08-05, receipts `~/.local/share/nx01/iter0095-design/`)

Orchestrator position ("invisible byte → fix the artifact") was REFUTED by
its own precommitted falsifier F2, fired by Codex with bytes and verified
by the orchestrator: Claude Code's Read output DOES represent a terminal
LF as a final empty numbered line (failing session Read tail `…\n98\t`,
passing session `…\n86\t`, no-LF control shows no extra numbered line).
The failing parent saw the cue and did not reproduce it. Adopted synthesis
(named criterion OBSERVABLE RECEIPT INTEGRITY): keep the byte-exact digest
gate and the 0094 verdict; the smallest change is a delivery-instruction
amendment, not gate softening, not artifact canonicalization.

## Candidate product change (route through /devlyn:resolve; executor pin applies)

Amend ONLY the Claude PLAN-delivery instruction in
`config/skills/devlyn:resolve/SKILL.md` PHASE 1 (+ `.agents`/`.claude`
mirrors), one sentence of substance: in Read output, a final empty
numbered line denotes the file's terminal LF — reproduce that LF at the
end of `Agent.prompt`; if no empty numbered line appears, do not add one.
No renderer change, no digest/oracle change, no normalization layer.
Escalation path (pre-named): if the explicit cue still fails a live 2/2
bar, THAT evidence justifies artifact canonicalization (renderer emits no
terminal LF) in a successor round — not before.

## What the registration must fold in (all evidence-backed, 2026-08-05)

1. **Instrument follow-up A — oracle evidence scoping** (registration-owned
   or product-landed via its own resolve run; adjudicate at freeze):
   current-format live sessions carry non-message JSONL records; the
   collector flags each as `message-not-object` and evidence-completeness
   caps classification at INCOMPLETE — no live arm can score COMPLETE.
   Proof by execution: retained 0091 C1 full-dir replay = INCOMPLETE with
   82 such issues (`~/.local/share/nx01/iter0091-stageb/canary1/result/plan-dispatch-oracle.json`)
   while the frozen "C1 stays COMPLETE" gate holds only on the curated
   self-test fixture. Scope: benign-record scoping + gate retained
   canaries on FULL-DIR replay (not fixtures) + rule the `subagent_type`
   absent-key tension (self-test :1474 vs the 0092 freeze's
   "leave selection to the parent / no key-set pin" prose — 0094 arms
   omitted it and were capped).
2. **Instrument follow-up B — dispatch-scorer artifacts clause**: align to
   the watcher's spawn-skeleton allowlist
   (`artifacts in (None, {}, {"findings_file": None, "log_file": None})`;
   product writer `state-phase-write.py:1350` emits the skeleton on every
   spawn); add BOTH selftest cases (skeleton → clean; genuinely non-null
   value → mutated); re-prove.
3. **Carry-over from 0094 (re-freeze, do not redesign)**: amended watcher
   copy (prep files allowed, `implement.stdout/stderr` forbidden), grace
   5000 ms (+ pre-arm SIGINT preflight), branch worktrees, fresh path per
   attempt, opaque arm tokens + sealed mapping commitment, neutral sibling
   base commits REGENERATED at the new candidate SHA (control = candidate
   tree with only the PLAN-dispatch product hunks reverse-applied — the
   0094 patch at `iter0094-reg/plan-dispatch-product.patch` plus the new
   instruction sentence), `--no-risk-probes` frozen invocation, pinned
   run-owned claude binary, sha-anchored frozen assets, fresh controls +
   fresh judging nonce (0088.3 rule; retire 0094's nonce).
4. **Bars**: candidate structural bar with **2/2 byte-exact deliveries**
   (digest conjunct unchanged); dispatch_clean (corrected scorer) all
   four arms; blind no-loser quality (Fable 5 + Grok 4.5, findings schema
   target `A|B|both` with file:line evidence MANDATORY — the citations are
   what made 0094's judge attribution swap mechanically provable);
   duration tripwires ≤1.25 / ≤1.50.
5. **Operator rules now default**: seat re-invocations carry a liveness
   marker + self-computed current-file sha (0094 measured a byte-identical
   stale re-emission from a Codex seat re-call); never `/login` while an
   arm is in flight; judge emissions = single JSON object only.

## Known satisfiability evidence (register as such)

The bar is satisfiable: 0094's candidate-simple delivered byte-exact WITH
the trailing LF through the same Read→transcribe route the instruction
targets. The retained LF/no-LF contrast pair is the registration's
satisfiability receipt.
