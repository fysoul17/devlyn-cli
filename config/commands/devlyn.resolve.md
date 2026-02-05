Perform deep root cause analysis for the following issue. Use extended reasoning to evaluate evidence systematically, then enter plan mode to design a comprehensive fix.

<issue>
$ARGUMENTS
</issue>

<default_to_plan_mode>
After completing root cause analysis, enter plan mode before implementing fixes. This ensures the user can review your understanding of the problem and approve your approach before changes are made.

Only skip plan mode if ALL conditions are true:
- Single-line or trivial change (typo, obvious syntax error)
- Exactly one correct solution with no alternatives
- Single file affected with no side effects

When in doubt, enter plan mode.
</default_to_plan_mode>

<investigate_before_answering>
ALWAYS read and inspect relevant files before forming hypotheses. Do not speculate about code you have not opened.

1. Read relevant files and error logs
2. Trace execution path from symptom to source
3. Map the code paths involved:

```
Entry: `file.ts:123` functionName()
  → calls `other.ts:45` helperFunction()
    → calls `service.ts:89` apiCall()
      → potential issue here
```

4. Find related test files that cover this area
5. Verify each assumption with actual code inspection

Evidence-based reasoning only. Every claim must reference specific file:line.
</investigate_before_answering>

<analysis_approach>
Apply the 5 Whys technique when root cause is not immediately obvious:
- Ask "why did this happen?" until you reach the fundamental cause
- Stop when you identify something actionable
- Document each "why" with supporting evidence

Generate 2-3 hypotheses with evidence:
1. **[Hypothesis]** - Evidence: [what supports this]
2. **[Hypothesis]** - Evidence: [what supports this]
</analysis_approach>

<test_driven_validation>
Before implementing the fix:

1. **Write a failing test** that reproduces the bug
2. **Implement fix** for most likely hypothesis
3. **Run test** - if fails, revert and try next hypothesis
4. **Iterate** until test passes
5. **Run full test suite** to check for regressions

If fix doesn't work, revert completely before trying next approach. Never layer fixes on top of failed attempts.
</test_driven_validation>

<no_fallbacks_or_workarounds>
Implement a robust fix that addresses the actual root cause. Do not:
- Add defensive fallbacks that mask problems (e.g., `|| defaultValue`)
- Hard-code values for the specific failing case
- Suppress errors without resolving the cause
- Use optional chaining (?.) to bypass null when null is the bug

Instead:
- Fix the code path that produces incorrect state
- Ensure solution works for all valid inputs
- Follow codebase's existing patterns
- Escalate blockers rather than shipping fragile patches
</no_fallbacks_or_workarounds>

<use_parallel_tool_calls>
Read multiple potentially relevant files in parallel. If the issue might involve 3 modules, read all 3 simultaneously.
</use_parallel_tool_calls>

<output_format>
Present findings before entering plan mode:

<root_cause_analysis>
**Symptom**: [What the user observed]
**Code Path**: [Entry point → ... → issue location with file:line]
**Root Cause**: [Fundamental issue with specific file:line]
**Hypotheses Tested**: [Which hypotheses were validated/invalidated]
**Why it matters**: [Impact if unfixed]
**Complexity**: [Simple fix / Multiple files / Architectural change]
</root_cause_analysis>

After fix is implemented:

<resolution>
**Fix Applied**: [file:line - what changed and why]
**Test Added**: [test file - what it validates]
**Verification**:
- [ ] Failing test now passes
- [ ] No regressions in test suite
- [ ] Manual verification (if applicable)
</resolution>
</output_format>

<next_steps>
1. If Complexity beyond "Simple fix" → enter plan mode immediately
2. In plan mode, present fix options if multiple valid solutions exist
3. Write failing test before implementing
4. Only mark complete after full test suite passes
</next_steps>
