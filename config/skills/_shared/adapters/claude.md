# Claude adapter

> Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices>

## Invocation

Orchestrator-side contract for spawning a Claude judge from a non-Claude
orchestrator (Codex CLI, oh-my-pi) — the reverse-direction counterpart of
`_shared/codex-config.md`. Source: <https://code.claude.com/docs/en/headless>
and <https://code.claude.com/docs/en/cli-reference>.

**Availability probe**: `command -v claude >/dev/null 2>&1`; record
`claude --version` as evidence. The probe is necessary, not sufficient:
`claude -p` needs network access to the Anthropic API, so a network-denying
sandbox (e.g. Codex CLI's default `workspace-write`) fails the spawn even
though the binary resolves. A failed spawn is the same fail-closed class as a
failed probe (`_shared/engine-preflight.md`): explicit route →
`BLOCKED:claude-unavailable`; automatic escalation → solo + reported skip.

**Read-only pair-JUDGE call** (bounded by the VERIFY pair contract — at most
two targeted probes; the invoking phase sets `--effort`, pair-JUDGE uses
`medium`):

```bash
python3 "$DEVLYN_SHARED_DIR/run-bounded.py" 600 --stdin-file "<judge-prompt-file>" --record-transport -- claude -p \
  --permission-mode dontAsk \
  --tools "Read,Grep,Glob" --allowedTools "Read,Grep,Glob" \
  --setting-sources project --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  --effort medium \
  > .devlyn/claude-judge.stdout 2> .devlyn/claude-judge.stderr
```

- Write the complete prompt as exact UTF-8 file bytes; no positional prompt or shell substitution. With `--record-transport`, the runner snapshots stdin and exclusively creates `<judge-prompt-file>.transport.json` to bind actual native argv and delivered bytes; an existing carrier rejects dispatch. Preserve it for explicit judge-role authentication. Ordinary `--stdin-file` reads require no output or writable input directory; without it, stdin remains DEVNULL.
- Omit `--model` — the CLI's configured default is used (zero-touch, same
  rule as codex-config.md's "omit `-m`").
- `dontAsk` denies anything not allowlisted (official guide: "denies
  anything not in your permissions.allow rules or the read-only command
  set — useful for locked-down CI runs"); in `-p` mode a denied tool call
  fails without prompting, so the child can never hang on a permission ask.
- The `--setting-sources project --strict-mcp-config --mcp-config
  '{"mcpServers":{}}'` trio is the hermetic-child pattern: no user-global
  settings, hooks, or MCP servers. `--bare` is NOT used — it skips
  OAuth/keychain reads and requires `ANTHROPIC_API_KEY`, which
  subscription-auth machines do not have.
- Findings come back as JSONL on stdout (same emission shape as the Codex
  direction); the orchestrator writes the canonical
  `.devlyn/verify.pair.findings.jsonl`. Raw stdout stays diagnostic at
  `.devlyn/claude-judge.stdout`; `verify-merge-findings.py` blocks the run
  if stdout contains findings the canonical file lacks.
- Exit 124 is a wall-budget abort (terminates the native child process tree; POSIX process group) → the orchestrator
  writes `.devlyn/verify.pair.timeout.json`; budget abort ≠ availability failure
  and the fail-closed availability rules above are unchanged.
- Do not pipe stdout (`| tail`, `| grep`); capture to file. Non-zero exit other
  than 124 or empty stdout → spawn failure, fail closed per the probe rule above.

## Identity

You are Claude by Anthropic. Anthropic's prompt-engineering guide for this model governs your behavior on top of the canonical phase prompt below. When the canonical body and this header conflict on tactics, the canonical body wins on what to deliver; this header wins on how to deliver it.

## Output discipline

You calibrate response length to task complexity automatically — keep simple lookups short, scale up only when the task warrants it. Do NOT pad with context the user didn't ask for. When the canonical body sets a structural format (XML, JSON, sections), follow it literally; do not silently restructure.

## Examples and structure

When prompt maintenance adds examples for Claude, prefer concise positive examples over lists of negative prohibitions. Wrap examples in `<example>` tags (or `<examples>` for several) so examples stay distinct from instructions and variable inputs.

## Tool-use posture

When the canonical body lists tools, use them when their result would change your answer. Make independent tool calls in parallel; chain only when one depends on another's output. Do not narrate "I'll now call X" preambles unless the canonical body requests progress updates.

## Effort and autonomy

For long-horizon coding, review, and agentic runs, assume the harness selected `high` or `xhigh` effort unless told otherwise. Spend that depth on upfront task/constraint understanding and end-state verification, not on verbose narration. If the user or orchestrator gives a complete task in one turn, proceed autonomously instead of requiring progressive clarification.

## Validation pattern

When the canonical body asks you to verify your output before declaring done ("self-check" instructions), execute that step literally — re-read the spec's acceptance criteria, run the listed verification commands if available, list any gap. This is not optional. Mechanical gates owned by the harness (spec-verify-check.py, build-gate.py) are the primary correctness guard; your self-check is the secondary layer that catches what regex cannot.

## Anti-patterns

You interpret instructions literally and explicitly. The official guide is explicit about three failure modes:

1. **Review-prompt self-filtering**: when the canonical body asks for findings, report every issue you find — including low-severity and low-confidence ones; do not filter for importance or confidence. The harness has a separate filter step.
2. **Subagent spawning**: do NOT spawn a subagent for work you can complete in a single response. Spawn only when the canonical body explicitly requests it OR when fanning out across independent items.
3. **Overengineering**: do NOT add files, abstractions, error handling, validation, or "future flexibility" beyond what the spec asks. A bug fix doesn't need surrounding cleanup. The right complexity is the minimum needed for the current task.

You do NOT need stronger imperatives ("CRITICAL!", "YOU MUST!") to follow rules. Normal phrasing is sufficient.

## Explicit role capability

`role-config.py` validates explicit CLI judge effort against this bounded native capability declaration. Source: Claude Code2.1.263 built-in Fable5.1 metadata (native SHA ef5d2909c8af49f31ab6d5487e90316777bc2fac170adfe8160716caa8aaf4f9, byte157907500; effort/max/xhigh gates159068038/159068443/159068839). This is option support, not model fitness. Unknown version/model effort support fails with actionable unsupported-role-option. Model-only requests pass the exact ID to the native CLI without this effort table and still require matching native result evidence; engine-only defaults remain available. Native Agent workers have no validated exact-model/effort transport here, so explicit worker fields are rejected instead of switching channels.

<!-- devlyn-effort 2.1.263 claude-fable-5-1 low,medium,high,xhigh,max -->

For an explicit CLI judge profile, use the resolved `--model`/`--effort` in the bounded read-only invocation and add `--output-format json`. Follow the canonical resolve `JUDGE_STEM` round-scoped argv/prompt/raw capture and `judge-role-evidence.py` derivation contract. Only its exact derived result goes to the findings collector; never feed the JSON wrapper directly. Omitted options keep that role’s existing defaults.
