**MEDIUM — P1’s Holm adjustment is undefined when P2 is unresolved.**

**Exact text:** [DESIGN.md:76](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-clause-ablation/autoresearch/experiments/0258/DESIGN.md:76) says “P1 and P2 form a two-test Holm family” and assigns `p = 1` when “adverse direction is absent.” The readiness and headline rules allow P1 rejection while P2 is unresolved, but do not specify that unresolved test’s adjustment input.

**Evidence:** With F10 C = 6/16 and B = 1/16, exact Fisher gives `p1 = 0.0414658262`. Retaining P2 internally as `p2 = 1` gives adjusted `p1 = 0.0829316525`, producing `P2_UNRESOLVED`. Passing only ready tests to the inherited [holm()](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-clause-ablation/autoresearch/experiments/0257/decide.py:67), whose multiplier uses `len(raw)`, instead produces `CLAUSE_IMPLICATED`. An unresolved result does not establish an absent direction.

**Fix:** Explicitly retain unresolved P2 as internal `p2 = 1` solely for Holm adjustment, while displaying `P2:NOT_READY`. Add this borderline example to qualification so readiness cannot silently reduce the family.

VERDICT: REVISE
