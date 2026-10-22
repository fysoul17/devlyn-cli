I'll review the 0257 design draft against the round-1 and round-2 notes and the 0256 records, without editing anything. First I'm loading the draft, the prior rounds, and the experiment apparatus.The draft is in hand. Next I will check its counts, witness rule, and schedule against the 0256 records and the §6 decision code.The Holm family, as written, does not control the false-rejection rate, and three run rules can still turn a partial or mixed run into a reading.

1. **Family membership and the power line disagree.** The family adds a witness only when \(n_B > n_A\). Dropping the other witnesses shrinks \(m\) and loosens every Holm threshold. Graded development rows are 28: D3 has 3 public checks plus D3.1–D3.6; D4 has 3 public checks plus D4.1-2, D4.3, D4.4, D4.5; I0185 has 1 public check plus heldout, release, alias, terminal-alias, and absence-lock; B5 has 1 public check plus 5 oracle rows. With 4 completion tests and 11 binding witnesses, \(m = 43\). The first threshold is \(0.05/43 \approx 0.001163\). Completion 16 vs 8 has one-sided \(p = 12870/10518300 \approx 0.001224\), so it does not reject, and the qualification line that calls it `PACKAGE_LOWERS_QUALITY` is false under this family. \(\alpha = 0.0125\) is \(0.05/4\). Power for a 1.0 vs 0.5 gap at \(0.05/43\) is \(P(\mathrm{Bin}(16,0.5) \le 7) = 26333/65536 \approx 0.40\). A D3/D4 oracle crash is stored as one new id, `D3.oracle` or `D4.oracle` (`0222/check.py`), which would join the family after the data. Confirmation uses “the same rule,” but no confirmation test is in the family, so its Fisher clause cannot reject.

**Fix:** Freeze 43 development tests per engine. A witness with \(n_B \le n_A\) stays in at \(p = 1\). Holm \(\alpha = 0.05\). A higher non-rejected witness remains `INCONCLUSIVE`. A crash is a fail on each frozen row of that task. Qualification: 16 vs 7 rejects (\(p = 11440/28048800 \approx 0.000408\)) when every other \(p\) is 1; 16 vs 8 does not. State gate power at \(0.05/43\). Give confirmation its own 11-test family (2 completions, F10’s 1 public and 4 oracle rows, F11’s 1 public and 3 oracle rows). It does not enter development’s family or gate.

2. **A new witness can be added after the trees are seen.** “Before any pooled count” still lets a mechanism found in the run enter the gate.

**Fix:** The binding set stays K2, K3, K4, K5, K7, K8, K10, X1, X2, W1, W2. Any new mechanism is run on every tree of its task and stays out of the family, the headline, and the token.

3. **An account change can finish inside one token.** “A changed account holds” is 0256’s resumable hold. That run updated the fingerprint and kept d14–c16 on a second account. A hold is not the stop rule’s identity failure.

**Fix:** A mismatch with the freeze fingerprint stops dispatch and the token stays `NOT_FINISHED`. Another account is a new registration.

4. **A prefix can hide harm, and the parser prediction can be won by missing probes.** 0256 `decide.py` returns `NOT_FINISHED` without evaluating `PACKAGE_UNSAFE`. Qualification checks a prefix and a false completion separately. Prediction 6 counts missing and unassessable probes as not JSON-error-400.

**Fix:** Qualify a prefix that contains one B false completion: headline `NOT_FINISHED`, clause list includes `PACKAGE_UNSAFE`, no Fisher \(p\) emitted. Score predictions 1–5 only on a finished panel. Score prediction 6 only when all 16 claude F10/F11 cells per arm are JSON-error-400, HTML-400, or other; otherwise leave it unscored.

VERDICT: REVISE
