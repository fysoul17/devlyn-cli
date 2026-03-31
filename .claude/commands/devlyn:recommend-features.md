---
description: Recommend top 5 feature specs based on product spec and codebase
allowed-tools: Bash(find:*), Bash(grep:*), Bash(wc:*), Bash(cat:*), Bash(ls:*), Bash(head:*), Bash(tail:*), Read, Glob
argument-hint: [focus-area or "all"]
---

<role>
You recommend which feature specs to generate next. Analyze product spec, existing specs, and codebase. Output top 5 prioritized by dependencies, value, and readiness.
</role>

<input>
$ARGUMENTS
</input>

<step_1_verify>

```bash
test -f docs/product-spec.md && echo "OK" || echo "MISSING"
```

```bash
ls docs/feature-specs/*.md 2>/dev/null || echo "NONE"
```

If product spec missing:

```
No product spec at docs/product-spec.md
Run /product-spec first.
```

Stop.
</step_1_verify>

<step_2_read_product_spec>
Read docs/product-spec.md.

Extract:

```yaml
platform: # from meta.platform
behaviors: # all behavior definitions
entities: # all entity definitions
views: # if section exists
commands: # if CLI platform
tools: # if MCP platform
functions: # if library/SDK platform
contracts: # if Web3 - contract definitions
instructions: # if Solana - program instructions
integrations: # external services
phases: # phase assignments
```

</step_2_read_product_spec>

<step_3_build_candidates>
Build candidate list from product spec sections that exist:

```yaml
sources:
  behaviors: # always - each behavior → candidate
  views: # if exists - each view → candidate
  commands: # if exists - each command → candidate
  tools: # if exists - each tool → candidate
  functions: # if exists - complex functions → candidate
  integrations: # if has business logic → candidate
  contracts: # if exists - each contract function → candidate
  instructions: # if Solana - each instruction → candidate
```

For each candidate:

```yaml
name: string
type: behavior | view | command | tool | function | integration | contract | instruction
phase: number
entities: [string]
depends_on: [string]
```

</step_3_build_candidates>

<step_4_check_existing_specs>

```bash
for f in docs/feature-specs/*.md; do
  [ -f "$f" ] && echo "$(basename "$f" .md)|$(grep -m1 '^status:' "$f" 2>/dev/null | cut -d: -f2 | xargs || echo 'draft')"
done
```

Mark each candidate:

- `specced: true` if file exists
- `spec_status: draft|ready|in-progress|done`

Filter to unspecced candidates only.
</step_4_check_existing_specs>

<step_5_analyze_codebase>
Detect stack:

```bash
ls package.json tsconfig.json pyproject.toml Cargo.toml go.mod CMakeLists.txt hardhat.config.js foundry.toml anchor.toml 2>/dev/null
```

Find source files:

```bash
find . -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.py" -o -name "*.go" -o -name "*.rs" -o -name "*.sol" -o -name "*.move" \) 2>/dev/null | grep -v node_modules | grep -v target | head -30
```

For each unspecced candidate:

```bash
grep -ril "{candidate_name}" src/ app/ lib/ cmd/ pkg/ contracts/ programs/ 2>/dev/null | head -3
```

Set `implementation: none | partial | exists`
</step_5_analyze_codebase>

<step_6_score>
Score each unspecced candidate:

```yaml
dependency: # 0-30
  30: no dependencies
  20: all dependencies have specs
  10: some dependencies missing specs
  0: blocked by unspecced dependency

value: # 0-25
  25: phase 1 AND core flow
  20: enables 2+ other features
  15: user/developer facing
  5: enhancement

readiness: # 0-20
  20: implementation exists
  15: partial implementation
  10: similar patterns exist
  5: greenfield

complexity: # 0-15 (simpler = higher)
  15: single entity, simple logic
  10: multiple entities, clear flow
  5: external integration
  0: complex state/transactions

urgency: # 0-10
  10: blocks other work
  5: natural next step
  2: can defer
```

`total = dependency + value + readiness + complexity + urgency`
</step_6_score>

<step_7_filter>
If $ARGUMENTS provided and ≠ "all":

```yaml
filters:
  core: phase = 1
  backend: type in [behavior, integration] AND NOT ui-only
  frontend: type = view OR has ui component
  api: behaviors with HTTP/RPC interface
  cli: type = command
  sdk: type = function
  mcp: type = tool
  auth: name contains auth|login|session|permission
  contract: type = contract
  onchain: type in [contract, instruction]
  solana: type = instruction
  { entity }: entities includes {entity}
  { phase_N }: phase = N
```

If no matches:

```
No unspecced features match "{$ARGUMENTS}".

Available filters:
{list applicable filters with counts}

Try: /recommend-features all
```

Stop.
</step_7_filter>

<step_8_output>
Sort by total score descending. Take top 5.

```markdown
## Feature Recommendations

**Product Spec:** v{version} · {platform} · {behavior_count} behaviors
**Existing Specs:** {count} ({done} done, {in_progress} in-progress)
**Focus:** {$ARGUMENTS or "all"}

---

### #1: {name}

**Score: {total}/100** · Phase {phase} · {type}

{One sentence why this ranks highest}

- Product Spec: `{section}.{name}`
- Entities: {list}
- Implementation: {status} {files if any}
- Dependencies: {✅ | ⏳ | ❌} {names}
```

/feature-spec {name}

```

---

### #2: {name}
**Score: {total}/100** · Phase {phase} · {type}

{reason}

- Product Spec: `{section}.{name}`
- Entities: {list}
- Implementation: {status}
- Dependencies: {status}

```

/feature-spec {name}

```

---

### #3: {name}
{same format}

---

### #4: {name}
{same format}

---

### #5: {name}
{same format}

---

## Dependency Order

{blocking relationships}

## Deferred

| Feature | Blocked By |
|---------|------------|
| {name} | {dependency} |
```

</step_8_output>

<all_specced>
If all candidates have specs:

```markdown
## All Features Specced

**Specs:** {count}

- Done: {n}
- In Progress: {n}
- Draft: {n}

Next:

1. Review drafts
2. Add features to product spec
```

</all_specced>
