# 0215 — reduce owner generations: remove the injected color detour

2026-09-23. User: design fewer owner generations, together with Astra. Root direct,
no resolve. Opus and Astra (gpt-6-astra/high, read-only) wrote independent R0s,
then cross-critiqued; Astra returned FREEZE in round 2. Design only: nothing dispatched.

## Why generations, and which ones

Each owner generation re-sends the whole context (12k–31k input in 0214 B), so
input tracks generation count ([0214 pilot](../0214/PILOT.md)). The ledger of
0213/0214 A and B (`.devlyn/0214-pilot/generations-0213-0214.md`) shows one
repeated avoidable block: 3–5 generations investigating two full-suite color
failures that exist on unmodified code (0213 A g6–8, 0213 B g6–8, 0214 A g7–10,
0214 B g7–11). Review launch/wait (1–2 generations) and post-review work are
smaller or carry required obligations; both stay unchanged here.

Why-chain: extra generations → owner diagnoses failures the evaluator never sees →
owner tool processes run with `NO_COLOR` set, while
[the evaluator](../0211/check_cell.py) runs `node --test` in a clean container →
the declared public check does not match the evaluator's environment.
Evidence: both 0214 owners' `checks-final/full.stdout` contain Node's warning
“The 'NO_COLOR' env is ignored…”, which requires `NO_COLOR` in the process env.
The image, container `--env` and plan argv set no color variable, so the Codex
exec layer is the injector **by elimination** (observed, not source-verified).

Model-free precheck (pinned image, unmodified D1 `ba6d13d`, no network):
clean 1372 pass/0 fail; `NO_COLOR=1` 1370/2; `NO_COLOR=1` with
`env -u NO_COLOR node --test` 1372/0; adding `TERM=dumb` changes nothing.

## Intervention (single variable)

Prefix both D1 public checks with `env -u NO_COLOR` so each declared check runs
in the evaluator's color environment. This fixes evaluator parity, not an owner
hint. Implement it as a 0215 wrapper around `0211/prepare.py`, like
`0214/prepare.py`, with the same prompt/argv/digest binding checks; archived
`0206/tasks.json` and every 0211–0214 file stay byte-identical. Keep the 0214
waiting text. No other prompt, owner.md, review, model/effort or budget change.
Not included: `-u NODE_DISABLE_COLORS` (no observed need), a 30000ms review
launch or evidence consolidation (second variables), a generation quota, or D3
(it shares commander but needs its own validation).

## Validation and prediction (stated before any run)

One fresh diagnostic-only D1 B cell under the 0214 setup, budgets and
first-breach stop rules; excluded from the cohort; no retry or C cell.
Historical 0213/0214 B runs are context, not a control; the claim is feasibility,
not attribution.

Prediction: the owner spends **zero** generations diagnosing color failures **and**
the cell is COMPLETE with terminal owner-plus-review input **< 400,000**.
Any color-diagnosis generation refutes the mechanism prediction; reaching 400,000
or UNKNOWN terminal usage refutes sufficiency. Weakened checks or a blinded-
assessment quality regression reject the change. A pass justifies replication
only, not adoption, a savings figure or proof of the injector.

**Strongest counter (Astra):** generation count is a proxy; fewer, larger turns can
cost more input, and cached input is not money. **Synthesis:** the registered
cache-inclusive input is the fixed objective; remove avoidable returns to the model
and measure full owner-plus-review input and quality, not count alone.

Evidence: `.devlyn/0215/` in the retained base checkout (both rounds' prompts
and answers, Opus R0, precheck).
