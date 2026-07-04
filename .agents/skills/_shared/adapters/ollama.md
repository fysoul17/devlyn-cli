# Ollama (local backend) adapter

> Source: <https://ai.google.dev/gemma/docs/core/prompt-structure> (official Gemma 1/2/3 prompt-structure guide; default model below is Gemma 3)

## Identity

You are a small local instruct model (default: `gemma3:4b`) running behind Ollama on `http://localhost:11434`. You have no tools, no file access, and no memory across calls — you answer only what is in the single prompt you receive. You fill exactly one role: VERIFY pair-JUDGE / risk-probe derivation. You are never the executor.

## Role eligibility

executor: no
pair_judge: yes

## Invocation

Availability probe (adapter-declared, per `_shared/engine-preflight.md#role-resolution`'s "an adapter may declare a different probe"): `curl -fsS -o /dev/null --connect-timeout 1 --max-time 2 http://localhost:11434/api/version`. A stopped server with the CLI installed is unavailable — same fail-closed contract as any other engine (`BLOCKED:ollama-unavailable`), not `command -v ollama`.

Request (`POST http://localhost:11434/api/generate`, `--max-time 60`):

```json
{"model":"gemma3:4b","prompt":"<bounded prompt: contract + diff + file excerpts>","stream":false,"format":{"type":"object","properties":{"findings":{"type":"array","items":{"type":"object","properties":{"id":{"type":"string"},"severity":{"type":"string","enum":["CRITICAL","HIGH","MEDIUM","LOW"]},"file":{"type":"string"},"line":{"type":"integer"},"summary":{"type":"string"}},"required":["id","severity","file","line","summary"]}}},"required":["findings"]}}
```

The orchestrator gathers the diff/contract/excerpts itself (this model cannot read files) and `json.loads` the response's `response` field: each `findings[]` element becomes one line of `.devlyn/verify.pair.findings.jsonl`; an empty array means PASS, matching the existing Codex pair-judge empty-file convention.

## Output discipline

Do not set a `system` field in the request — Gemma has no system role (official guide: "the `system` role or a system turn is not supported"); fold the full judge contract into `prompt` as the user turn. Never ask this model to run commands or open files; it cannot.

## Anti-patterns

1. **Do not trust free-form JSONL text from this model.** Unconstrained generation wraps output in markdown fences and drifts from a line-delimited contract (verified empirically, iter-0051 smoke test). Always set `format` to the findings-array schema above and let the orchestrator do the mechanical JSONL serialization — never ask the model to emit JSONL text directly.
2. **Do not treat this as an agentic pair judge.** It cannot run the "at most two targeted probes... using the repo's CLI/API/test runner" contract in `verify.md`'s pair-mode section the way Codex/Claude do — the orchestrator must pre-select and paste the relevant diff hunks and file excerpts into `prompt` instead.
