# iter-0112 — venue-tolerant session-horizon measurement (STUB; R0 pending)

Status: STUB 2026-08-31 (session 17). Successor to iter-0110 (TERMINAL `VENUE_REJECTED`, DECISIONS 0110.1 — the frozen design passed its serial A5 gate in all four roots; the shared-account venue killed every root: session limits ×2, a 429 burst, a weekly limit). **USER RULING binds: the venue IS the shared account (D declined). The successor treats provider/account limits as a design constraint, not an operational hazard.**

## Fixed inputs (carried from 0110, not re-litigated in R0)

- Estimand family: opus-5 vs opus-4-8 late-minus-early interaction ΔH on real resume-chain sessions (0110 registration), unless open question (a) forces a budget-driven revision.
- sol V5 successor inputs (m6 verify, `m6cap-sol.log`): persist per-task CLI rc in the driver (C-RC class was undiagnosable without it); pre-register whether AUP/policy-refusal session-endings belong to the estimand (engine-differential, task-clustered in m6); pre-register host-network failure disposition (C-NET class).
- Window-key rule (0110 AMENDMENT 6 rule 7): API-level evidence only; machine-local transcript chaining stays retired.
- Launch discipline: nothing fires before 2026-09-05 08:00 KST (weekly reset); peer-lane window grants respected.

## Open questions for R0 (three-way: fable + sol; grok opportunistic — skip on 402)

(a) **BUDGET FIRST — was m6's weekly-limit death self-inflicted?** Numerator MEASURED 2026-08-31 (transport `modelUsage` fields only, 568 receipts / 79 sessions, outcomes never opened; weekly window anchor = Fri 08-29 08:00 KST per the reset receipt, so ALL of m6 sits inside the window that died): **output 3.12M tokens (opus-5 1.64M / opus-4-8 0.79M / sonnet 0.70M), cacheCreate 7.37M, input 11K, cacheRead 379.5M** — a full 120-session root ≈ 1.5× that. The DENOMINATOR (weekly allowance, plus the co-consumers' share: interactive sessions, archon/superset/pyx automations) is not in receipts — R0 must pick the instrument (`/usage` readouts are the API-level candidate) and rule whether S=5 fits a weekly envelope alongside normal use. If not, the design shrinks (S, K, or engine count) into a registered budget envelope; no recoverability amendment can save an over-budget root.

(b) **Survivable unit.** 0110's fatal coupling was root-serial contemporaneity: a limit event voids blocks, cap 2, root dies. Candidates: (i) multi-day root with block replay across windows (drop contemporaneity — cost to the crossover?), (ii) a smaller registered unit that completes inside one session window, (iii) a pre-block headroom oracle (usage-probe gate; registered pause-not-death). Decisive-criterion candidate: SCORED-ROOT SURVIVABILITY under the OBSERVED limit-class distribution (2 session / 1 burst / 1 weekly).

(c) **m6 salvage.** May 0112 register a PROSPECTIVE join rule over m6's 12 designated blocks (outcomes never opened; join semantics frozen before any manifestation field is read), or is cross-registration contamination disqualifying? If inadmissible, the blocks stay diagnostics forever.

(d) **Corpus.** Keep the 0102-derived task set (AUP-prone tasks included, with the registered estimand ruling from (fixed inputs)) or re-derive?

R0 output = registered contract + falsifiers + apparatus delta list vs the 0110 frozen set → terra implementation → trio freeze → launch USER-GATED (post 09-05).
