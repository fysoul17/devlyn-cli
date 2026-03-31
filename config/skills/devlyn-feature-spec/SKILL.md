---
description: Generate a Feature Spec document from product spec behavior
allowed-tools: Bash(cp:*), Bash(mkdir:*), Bash(find:*), Bash(grep:*), Bash(cat:*), Bash(ls:*), Read, Write, Edit
argument-hint: [feature-name]
---

<role>
You generate feature specs. Transform product spec behaviors into implementable specifications. Adapt sections based on platform type from product spec.
</role>

<input>
$ARGUMENTS
</input>

<step_1_verify>

```bash
test -f docs/product-spec.md && echo "OK" || echo "MISSING"
```

If missing:

```
No product spec at docs/product-spec.md
Run /product-spec first.
```

Stop.

```bash
mkdir -p docs/feature-specs
```

</step_1_verify>

<step_2_read_product_spec>
Read docs/product-spec.md.

Extract:

```yaml
platform: # from meta.platform
behaviors: # all behaviors
entities: # all entities
views: # if defined
integrations: # if defined
```

</step_2_read_product_spec>

<step_3_find_feature>
Search for $ARGUMENTS in:

1. `behaviors[].name`
2. `views[].name` (if exists)
3. `entities[].name`

If not found:

```
Feature "{$ARGUMENTS}" not found in product spec.

Available behaviors:
{list behavior names}

Run /recommend-features to see prioritized list.
```

Stop.

Extract related content for this feature:

```yaml
behavior: # matched behavior definition
entities: # entities involved
views: # views if any
permissions: # if defined
errors: # error cases
integrations: # if uses external services
```

</step_3_find_feature>

<step_4_detect_interfaces>
Determine interface types from `meta.platform`:

```yaml
web: [api, ui]
mobile: [api, ui]
desktop: [api, ui]
cli: [commands]
api: [api]
library: [public_api]
sdk: [public_api]
service: [api, events, jobs]
worker: [jobs, events]
mcp: [tools, resources]
embedded: [hardware, protocols]
smartcontract: [contract_functions, contract_events, storage]
solidity: [contract_functions, contract_events, storage]
solana: [instructions, accounts, events]
web3: [contract_functions, contract_events, storage]
blockchain: [contract_functions, contract_events, storage]
```

If platform not specified, infer from:

- Has `views` section → include ui
- Has HTTP behaviors → include api
- Has CLI behaviors → include commands
- Has async behaviors → include jobs/events
- Has `contracts` section → include contract interfaces
- Has `.sol` files in codebase → include contract interfaces
  </step_4_detect_interfaces>

<step_5_analyze_codebase>

```bash
ls package.json tsconfig.json pyproject.toml Cargo.toml go.mod hardhat.config.js foundry.toml anchor.toml 2>/dev/null
```

```bash
find . -type f \( -name "*.ts" -o -name "*.py" -o -name "*.go" -o -name "*.rs" -o -name "*.sol" -o -name "*.move" \) 2>/dev/null | grep -v node_modules | head -20
```

```bash
grep -ril "{$ARGUMENTS}" src/ app/ lib/ contracts/ programs/ 2>/dev/null | head -5
```

If `.sol` files found → set `interfaces += [contract_functions, contract_events, storage]`
If `programs/` or `anchor.toml` found → set `interfaces += [instructions, accounts, events]`
</step_5_analyze_codebase>

<step_6_check_template>

```bash
cat .claude/templates/feature-spec.md 2>/dev/null || echo "NO_TEMPLATE"
```

If template exists, use its structure with platform adaptations.
</step_6_check_template>

<spec_sections>
Include sections based on detected interfaces:

## Meta (always)

```yaml
id: F-{number}
status: draft
version: "0.1"
created: { today }
product_spec: "{behavior_name}"
phase: { phase }
platform: { platform }
interfaces: [{ detected interfaces }]
```

## Overview (always)

```yaml
purpose: { one sentence }
success_criteria:
  - { measurable outcome }
```

## Data Model (if has entities)

### {EntityName}

```yaml
attributes:
  { field }:
    type: { type }
    required: { bool }
    constraints: { rules }

relations:
  { name }:
    type: { relation_type }
    target: { Entity }

examples:
  typical: { value }
  edge: { value }
```

If has lifecycle:

```yaml
states:
  { state }:
    transitions:
      - to: { next }
        trigger: { action }
```

---

## API (if api in interfaces)

### {METHOD} {/path}

```yaml
purpose: { description }
auth: { required|optional|public }

request:
  body: {}

response:
  success:
    status: { code }
    body: {}
  errors:
    - code: { ERROR_CODE }
      when: { condition }
      message: { text }
```

---

## CLI (if commands in interfaces)

### {command}

```yaml
usage: {program} {command} [options] <args>

arguments:
  {arg}:
    required: {bool}
    description: {text}

options:
  --{flag}:
    short: -{f}
    type: {type}
    default: {value}

output:
  success: {format}
  error: {format}
  exit_codes:
    0: success
    1: {error}

examples:
  - cmd: {example}
    desc: {what it does}
```

---

## Public API (if public_api in interfaces)

### {function_name}

```yaml
signature: { full signature }

parameters:
  { param }:
    type: { type }
    description: { text }

returns:
  type: { type }
  description: { text }

throws:
  - { Error }: { when }

example: |
  {code}
```

### {ClassName}

```yaml
purpose: { description }

constructor:
  params: {}

methods:
  { method }: { signature }

properties:
  { prop }: { type }
```

---

## MCP (if tools/resources in interfaces)

### Tool: {name}

```yaml
description: { what it does }

parameters:
  { param }:
    type: { type }
    required: { bool }

returns: { description }
```

### Resource: {uri}

```yaml
uri_template: { template }
mime_type: { type }
```

---

## UI (if ui in interfaces)

### {ViewName}

```yaml
route: { path }
layout: { type }

states:
  loading: { shows }
  empty: { shows }
  error: { shows }
  success: { shows }

flow: 1. {step}
```

---

## Events (if events in interfaces)

### {event_name}

```yaml
trigger: { when }
payload:
  { field }: { type }
subscribers: [{ who }]
```

---

## Jobs (if jobs in interfaces)

### {job_name}

```yaml
trigger: { schedule|event|manual }
schedule: { cron }
input: {}
output: {}
timeout: { duration }
retry: { strategy }
```

---

## Hardware (if hardware in interfaces)

### {interface_name}

```yaml
protocol: { type }
pins: [{ list }]
timing: { constraints }
commands:
  { cmd }: { description }
```

---

## Contract (if contract_functions in interfaces)

### {ContractName}

```yaml
purpose: { description }
inherits: [{ parent contracts }]
```

### State

```yaml
{ variable }:
  type: { solidity type }
  visibility: { public|private|internal }
  description: { purpose }
```

### Functions

#### {function_name}

```yaml
visibility: { external|public|internal|private }
mutability: { view|pure|payable|nonpayable }
modifiers: [{ modifier }]

parameters:
  { param }:
    type: { solidity type }
    description: { text }

returns:
  { name }: { type }

requires:
  - { condition }: { revert message }

emits:
  - { EventName }

gas_estimate: { approximate }
```

### Events

```yaml
{ EventName }:
  params:
    { param }:
      type: { type }
      indexed: { bool }
  emitted_when: { condition }
```

### Modifiers

```yaml
{ modifier_name }:
  purpose: { description }
  requires: [{ conditions }]
```

### Access Control

```yaml
roles:
  { ROLE_NAME }:
    can: [{ functions }]
    granted_by: { who }
```

### Upgradability (if applicable)

```yaml
pattern: { transparent|uups|beacon|diamond }
storage_layout: { considerations }
```

---

## Solana Program (if instructions in interfaces)

### {ProgramName}

```yaml
program_id: { pubkey or TBD }
```

### Accounts

```yaml
{ AccountName }:
  seeds: [{ seed derivation }]
  space: { bytes }
  fields:
    { field }:
      type: { borsh type }
      offset: { bytes }
```

### Instructions

#### {instruction_name}

```yaml
discriminator: { 8 bytes }

accounts:
  { account }:
    is_mut: { bool }
    is_signer: { bool }
    description: { text }

args:
  { arg }:
    type: { borsh type }

logic: { description }

emits:
  - { event }
```

### Events

```yaml
{ EventName }:
  fields:
    { field }: { type }
```

---

## Business Logic (always)

### Rules

```yaml
- rule: { name }
  when: { condition }
  then: { action }
```

### Validations

```yaml
- field: { name }
  rules: [{ validation }]
  message: { error }
```

### Permissions (if defined)

```yaml
{ action }: { who }
```

---

## Integrations (if has external services)

```yaml
- service: { name }
  operation: { what }
  fallback: { if fails }
```

---

## Test Scenarios (always)

### Unit

```yaml
- scenario: { description }
  given: { setup }
  when: { action }
  then: { result }
```

### Edge Cases

```yaml
- case: { description }
  input: { value }
  expected: { handling }
```

---

## Dependencies (always)

```yaml
requires:
  - { feature }: { status }
enables:
  - { feature }
```

## Open Questions

- [ ] {question}
      </spec_sections>

<step_7_write>
Write to: `docs/feature-specs/{$ARGUMENTS}.md`

Include only sections for detected interfaces.
Use kebab-case filename.
</step_7_write>

<step_8_output>

```markdown
## Feature Spec Generated

**File:** `docs/feature-specs/{name}.md`
**Platform:** {platform}
**Interfaces:** {list}

### Summary

- Behavior: {name}
- Entities: {count}
- {interface_type}: {count} (e.g., "Endpoints: 3" or "Commands: 2" or "Functions: 5")

### Dependencies

- ✅ {specced}
- ❌ {missing} → `/feature-spec {name}`
```

</step_8_output>

<update_mode>
If file exists at `docs/feature-specs/{$ARGUMENTS}.md`:

Read existing. Apply targeted changes. Update version.

```markdown
## Feature Spec Updated

**Version:** {old} → {new}

### Changes

- {change}
```

</update_mode>
