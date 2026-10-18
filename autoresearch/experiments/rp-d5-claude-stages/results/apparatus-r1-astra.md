Three **MEDIUM** findings; no HIGH findings.

1. **MEDIUM — An effort STOP during the first smoke still permits the spare.**  
   The inherited [smoke closure](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d4-helper-report/runner.py:281) converts a first-attempt STOP without credential revocation into registry status `FAILED`. [Spare staging](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d5-claude-stages/stage.py:32) then accepts it. This violates DESIGN’s requirement that an effort mismatch stop the run before the next slot.  
   **Fix:** Preserve terminal STOP for effort-binding failure and reject the spare. Add a mismatch→spare-refusal test while retaining the spare for ordinary delivery failure.

2. **MEDIUM — Nonliteral `open()` modes can falsely establish the first write.**  
   The [literal-mode regex](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d5-claude-stages/attribute.py:240) accepts `"w" if flag else "r"` as a literal. Reproduction produced **Edit → Verify**, with the Explore/Verify split marked supported. DESIGN requires **Other → Explore**, with an unsupported split.  
   **Fix:** Parse the mode expression and accept only a string constant; classify other expressions as unknown. Add conditional and concatenation cases to the oracle.

3. **MEDIUM — Shell-read operand parsing changes attribution incorrectly.**  
   [read_paths()](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d5/autoresearch/experiments/rp-d5-claude-stages/attribute.py:144) produces:
   - `rg CLAUDE.md -e needle` → **Explore**, instead of **Orient**.
   - `grep CLAUDE.md -f /tmp/patterns` → **Explore**, instead of **Orient**.
   - `cat CLAUDE.md >/tmp/copy` → **Other**, instead of **Orient**.

   **Fix:** Collect explicit-pattern options before assigning positional arguments, and remove actual redirection syntax from read operands while preserving quote information. Add both option orders and excluded-redirection cases.

The remaining source paths checked out: verified registry 4.2.22 only; fixed schedule/repository names; retained local evidence; PAT, bundled Codex and Claude bearer scans before sealing; and the 6300-second floor. Effort reaches the launch through `--effort`, `CLAUDE_CODE_EFFORT_LEVEL`, and settings. The separate sealed-request check catches mismatches despite an unrelated auditor rejection. Exact Claude Code 2.1.296 execution was not available for independent verification.

All explicitly named DESIGN oracle cases are represented. No additional defect was found in 0254 reconciliation, prediction checks, or efficiency eligibility.

Validation: **23 filesystem-free pytest cases and 56 in-memory Bash oracle cases passed**. The full README suites were blocked before collection because the read-only sandbox provides no writable temporary directory. No files changed; no Docker, network, or credentials used.

VERDICT: REVISE
