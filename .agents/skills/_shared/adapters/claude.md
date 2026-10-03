# Claude adapter

> Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices>

## Invocation

`verify-judges.py` spawns every Claude VERIFY judge, primary or pair, from any
orchestrator. Source: <https://code.claude.com/docs/en/headless> and
<https://code.claude.com/docs/en/cli-reference>.

**Availability probe**: `command -v claude >/dev/null 2>&1`; record
`claude --version` as evidence. The probe is necessary, not sufficient:
`claude -p` needs network access to the Anthropic API, so a network-denying
sandbox (e.g. Codex CLI's default `workspace-write`) fails the spawn even
though the binary resolves. A failed spawn is the same fail-closed class as a
failed probe (`_shared/engine-preflight.md`): explicit route →
`BLOCKED:claude-unavailable`; automatic escalation → solo + reported skip.

**Read-only judge call** (the pair seat defaults to `--effort medium`; the
primary omits effort and model unless its profile sets them):

```bash
python3 "$DEVLYN_SHARED_DIR/run-bounded.py" 600 --stdin-file .devlyn/claude-judge.r<round>.prompt --record-transport -- claude -p \
  --permission-mode dontAsk \
  --tools "Read,Grep,Glob" --allowedTools "Read,Grep,Glob" \
  --setting-sources project --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  [--model <model>] [--effort <effort>] --output-format json --json-schema '<judge schema>'
```

- `--json-schema` carries `judge-role-evidence.py`'s `JUDGE_SCHEMA`; the harness validates the envelope's `structured_output` and renders it as the seat's canonical JSONL, findings then the verdict line.
- The prompt travels as exact file bytes on stdin; `--record-transport` binds the delivered bytes, actual native argv, runner outcome and timing in `<prompt>.transport.json`.
- `dontAsk` denies anything not allowlisted (official guide: "denies
  anything not in your permissions.allow rules or the read-only command
  set — useful for locked-down CI runs"); in `-p` mode a denied tool call
  fails without prompting, so the child can never hang on a permission ask.
- The `--setting-sources project --strict-mcp-config --mcp-config
  '{"mcpServers":{}}'` trio is the hermetic-child pattern: no user-global
  settings, hooks, or MCP servers. `--bare` is NOT used — it skips
  OAuth/keychain reads and requires `ANTHROPIC_API_KEY`, which
  subscription-auth machines do not have. The supervisor removes an inherited
  `CLAUDECODE` so the nested CLI starts.

### Explicit role capability

`role-config.py` validates explicit CLI judge effort against this bounded native capability declaration. Source: Claude Code2.1.263 built-in Fable5.1 metadata (native SHA ef5d2909c8af49f31ab6d5487e90316777bc2fac170adfe8160716caa8aaf4f9, byte157907500; effort/max/xhigh gates159068038/159068443/159068839). This is option support, not model fitness. Unknown version/model effort support fails with actionable unsupported-role-option. Model-only requests pass the exact ID to the native CLI without this effort table and still require matching native result evidence; engine-only defaults remain available. Native Agent workers have no validated exact-model/effort transport here, so explicit worker fields are rejected instead of switching channels.

<!-- devlyn-effort 2.1.263 claude-fable-5-1 low,medium,high,xhigh,max -->

`verify-judges.py` adds a validated explicit `--model`/`--effort` field by field; omitted options keep that seat's defaults.

## Identity

You are Claude by Anthropic. Anthropic's prompt-engineering guide for this model governs your behavior on top of the canonical phase prompt below.

## Output discipline

You calibrate response length to task complexity automatically — keep simple lookups short, scale up only when the task warrants it. Do NOT pad with context the user didn't ask for. When the canonical body sets a structural format (XML, JSON, sections), follow it literally; do not silently restructure. In a VERIFY judge seat started with a JSON schema, return the findings and verdict only through the structured-output tool.

## Examples and structure

When prompt maintenance adds examples for Claude, prefer concise positive examples over lists of negative prohibitions. Wrap examples in `<example>` tags (or `<examples>` for several) so examples stay distinct from instructions and variable inputs.

## Tool-use posture

When the canonical body lists tools, use them when their result would change your answer. Make independent tool calls in parallel; chain only when one depends on another's output. Do not narrate "I'll now call X" preambles unless the canonical body requests progress updates.

## Effort and autonomy

For long-horizon coding, review, and agentic runs, assume the harness selected `high` or `xhigh` effort unless told otherwise. Spend that depth on upfront task/constraint understanding and end-state verification, not on verbose narration. If the user or orchestrator gives a complete task in one turn, proceed autonomously instead of requiring progressive clarification.

## Anti-patterns

You interpret instructions literally and explicitly. The official guide is explicit about three failure modes:

1. **Review-prompt self-filtering**: when the canonical body asks for findings, report every issue you find — including low-severity and low-confidence ones; do not filter for importance or confidence. The harness has a separate filter step.
2. **Subagent spawning**: do NOT spawn a subagent for work you can complete in a single response. Spawn only when the canonical body explicitly requests it OR when fanning out across independent items.
3. **Overengineering**: do NOT add files, abstractions, error handling, validation, or "future flexibility" beyond what the spec asks. A bug fix doesn't need surrounding cleanup. The right complexity is the minimum needed for the current task.

You do NOT need stronger imperatives ("CRITICAL!", "YOU MUST!") to follow rules. Normal phrasing is sufficient.
