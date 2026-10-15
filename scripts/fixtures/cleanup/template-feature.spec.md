# {Feature Name}

## Meta

```yaml
id: F-{number}
status: draft
version: "0.1"
created: { date }
product_spec: "{behavior}"
phase: { phase }
platform: { platform }
interfaces: [{ list }]
```

## Overview

```yaml
purpose: { one sentence }
success_criteria:
  - { outcome }
```

---

## Data Model

### {Entity}

```yaml
attributes:
  { field }:
    type: { type }
    required: { bool }
    constraints: { rules }

relations:
  { name }:
    target: { Entity }
    type: { relation }

examples:
  typical: {}
  edge: {}
```

---

<!-- Include sections based on interfaces[] -->

## API

<!-- if: api in interfaces -->

### {METHOD} {/path}

```yaml
purpose: { text }
auth: { level }
request: {}
response:
  success: {}
  errors: []
```

---

## CLI

<!-- if: commands in interfaces -->

### {command}

```yaml
usage: { pattern }
arguments: {}
options: {}
output: {}
examples: []
```

---

## Public API

<!-- if: public_api in interfaces -->

### {function}

```yaml
signature: { sig }
parameters: {}
returns: {}
throws: []
```

---

## MCP

<!-- if: tools in interfaces -->

### Tool: {name}

```yaml
description: { text }
parameters: {}
returns: { text }
```

---

## UI

<!-- if: ui in interfaces -->

### {View}

```yaml
route: { path }
states: {}
flow: []
```

---

## SmartContract (EVM, non-EVM like Solana)

<!-- if: contract_functions in interfaces -->

### State

```yaml
{ variable }:
  type: { type }
  visibility: { visibility }
```

### Functions

#### {function}

```yaml
visibility: { external|public }
mutability: { view|pure|payable }
modifiers: []
parameters: {}
returns: {}
requires: []
emits: []
```

### Events

```yaml
{ Event }:
  params: {}
  indexed: []
```

### Access Control

```yaml
roles: {}
```

---

## Events

<!-- if: events in interfaces -->

### {event}

```yaml
trigger: { when }
payload: {}
```

---

## Jobs

<!-- if: jobs in interfaces -->

### {job}

```yaml
trigger: { type }
schedule: { cron }
input: {}
output: {}
```

---

## Business Logic

### Rules

```yaml
- rule: { name }
  when: { condition }
  then: { action }
```

### Validations

```yaml
- field: { name }
  rules: []
  message: { text }
```

---

## Integrations

<!-- if: has external services -->

```yaml
- service: { name }
  operation: { what }
  fallback: { backup }
```

---

## Test Scenarios

### Unit

```yaml
- scenario: { text }
  given: { setup }
  when: { action }
  then: { result }
```

### Edge Cases

```yaml
- case: { text }
  input: { value }
  expected: { handling }
```

---

## Dependencies

```yaml
requires: []
enables: []
```
