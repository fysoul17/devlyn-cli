VERDICT: REVISE
FINDINGS:

- [HIGH] `0260/RESULT.md:124,157` and `0259/erratum-1.md:30` — The single-server exceptions omit explicit headings: c012 says “One server process per file”; 0259 c002 says “One server process only.” Both witnesses reproduce acknowledged-item loss twice. — Apply the chosen process-boundary judgment consistently: count both as false completions, updating judgments, totals, erratum, pointer and DECISIONS. This alone changes 0260 B to 6 and 0259 C to 8.

- [HIGH] `0260/results/decisions-audit.json:108` and `0260/RESULT.md:182` — c011 promises serialization for the “same file,” but keys queues by unnormalized path strings. Relative and absolute paths are ordinary `createApp` inputs; the identical-path witness does not address this counterexample. — Run an own-tree absolute/relative-path witness checking every acknowledged item, then adjudicate c011 before clearing it.

- [MEDIUM] `0260/RESULT.md`, `0259/erratum-1.md` and `autoresearch/DECISIONS.md` — Current judgments contain **10**, not eleven, process-class false completions, and **8**, not seven, losing-tree exemptions. All **32** 0259 reports contain process-boundary wording, including qualified wording. — Reconcile every count after readjudgment; explicitly define any narrower category behind “31.”

- [LOW] `0260/RESULT.md:230–232` — The five driver-level HTTP 429 holds and two cell-preflight HTTP 429 refusals are separate events; “Two of the 429s” incorrectly treats the latter as a subset. — State “five driver-level 429 holds, plus two preflight 429 refusals; both slots were retried.”
