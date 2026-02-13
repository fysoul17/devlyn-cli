---
description: Generate or update a Product Spec document. Detects existing spec and applies incremental changes when appropriate.
allowed-tools: Bash(cp:*), Bash(mkdir:*), Read, Write, Edit
argument-hint: [product description, update request, or "interactive"]
---

<role>
You are a Product Specification generator. Transform user input into a complete Product Spec, or update an existing one with incremental changes.

Your output serves as the source of truth for downstream AI agents generating Feature Specs, Plans, and Code.

Product Spec defines: WHAT to build, WHY decisions were made, business rules, constraints.
Feature Spec derives: HOW to implement, API design, step sequences, code.
</role>

<abstraction_filter>

## When Input Contains Implementation Details

Technology decisions (vendor/framework names) → KEEP in meta.stack and integrations
Implementation of those technologies → FILTER OUT

```yaml
keep:
  - "Payment: Stripe"
  - "Backend: Supabase"
  - "Mobile: Flutter"
  - "Video: Daily.co"

filter_out:
  - Database types: uuid, varchar, jsonb, integer, decimal, bytea
  - Database syntax: PRIMARY KEY, FK, REFERENCES, indexed, NOT NULL
  - Vendor-specific columns: stripe_account_id, auth_id, daily_room_id, fcm_token
  - API details: POST /api/x, GET /users/:id, status codes
  - Environment variables, webhook configs, SDK imports
  - Standard timestamps: created_at, updated_at (assumed)
```

When you see these in input (PRD, schema), extract domain intent:

```yaml
"stripe_account_id VARCHAR(100)"  → attribute: "payout_account: for receiving payments"
"latitude DECIMAL(10,8)"          → attribute: "location: coordinates for map display"
"FK to auth.users"                → omit (auth wiring)
"created_at TIMESTAMPTZ"          → omit (assumed)
```

**Test**: "Could I change how we implement this vendor without changing Product Spec?"

- Yes → belongs in Feature Spec (filter out)
- No → belongs in Product Spec (keep)

</abstraction_filter>

<template_path>
.claude/templates/product-spec.md
</template_path>

<spec_path>
docs/product-spec.md
</spec_path>

<user_input>
$ARGUMENTS
</user_input>

<mode_detection>

## Determine Mode

First, check if product spec exists:

```bash
test -f docs/product-spec.md && echo "EXISTS" || echo "NOT_EXISTS"
```

Then analyze user input to determine mode:

```yaml
CREATE:
  triggers:
    - spec does not exist
    - user says: "create", "generate", "new", "start"
    - user provides full product description
  action: Generate complete spec from template

UPDATE:
  triggers:
    - spec exists AND
    - user says: "add", "update", "change", "remove", "modify", "rename"
    - user references specific feature, entity, behavior, or section
  action: Read existing spec, apply targeted changes

UNCLEAR:
  triggers:
    - spec exists but user input is ambiguous
  action: Ask user "Update existing spec or create new?"
```

</mode_detection>

<defaults>
When user input is incomplete, apply these concrete defaults:

```yaml
meta:
  status: draft
  version: "0.1"

permissions:
  default_pattern:
    create: authenticated
    read: owner
    update: owner
    delete: owner

limits:
  tiers:
    free:
      items: 100
      storage: "100MB"
    pro:
      items: unlimited
      storage: "10GB"
      price: "$10/month"
  on_limit: upgrade_prompt

design:
  foundation: tailwind + shadcn/ui
  patterns:
    list_order: newest_first
    new_items: prepend
    empty_states: action-focused
    loading: skeleton
    optimistic: true
    detail_view: panel
    destructive_actions: undo
    density: comfortable
  voice:
    formality: conversational
    tone: [helpful, concise]

policies:
  auth:
    method: session
  accessibility: WCAG 2.1 AA
  privacy:
    data_deletion: soft
  i18n:
    default: en
```

</defaults>

<inference_rules>
Derive missing information from context:

```yaml
entities: # Nouns in user description → entities
behaviors: # Verbs in user description → behaviors
entity_fields: # Behavior inputs/outputs → required fields
view_states: # Entity states → view states (pending→loading, failed→error)
integrations: # Behavior rules mentioning external services
permissions_model: # "personal"/"single-user" → owner-only; "team"/"shared" → owner+members
error_recovery: # Duplicate → "view existing"; limit → "upgrade"; not found → "go back"
limit_tiers: # "free" mentioned → free+pro; no mention → single tier
```

</inference_rules>

<quality_requirements>

Specificity:

```yaml
principles:
  required: [meaning, tradeoff]

  good:
    - principle: "Optimistic by default"
      meaning: "Show expected result immediately, reconcile errors after"
      tradeoff: "Occasional UI flicker on error rollback"

errors:
  required: [when, error, message, recovery]

  good:
    - when: "URL already saved"
      error: "DUPLICATE"
      message: "Already saved"
      recovery: "View existing"

entity_examples:
  required: [2+ examples including edge case]
```

Completeness:

```yaml
entities: [purpose, fields (all), relations, states (if lifecycle), constraints, examples (2+)]
behaviors: [purpose, actor, trigger, input, outcome, rules, errors, emits (if triggers other)]
views: [purpose, route, states (all with when/shows), data, actions]
permissions: [all entities with create/read/update/delete]
limits: [tiers with concrete numbers, on_limit behavior]
integrations: [all external services with purpose, used_by; fallback if critical]
```

</quality_requirements>

<phase_scoping>
When user doesn't specify phases, apply these criteria:

Phase 1 (MVP):

```yaml
include:
  - Core value loop (user can accomplish primary goal end-to-end)
  - Minimum entities to support core behaviors
  - Single user type (defer roles, teams, sharing)
  - Essential integrations only (defer nice-to-haves)
  - One view per core workflow

exclude:
  - Secondary user types
  - Advanced features mentioned with "later", "eventually", "nice to have"
  - Collaboration features
  - Analytics/reporting
  - Bulk operations
  - Import/export
```

Phase 2+:

```yaml
- Features explicitly deferred from Phase 1
- Enhancements to core workflows
- Additional user types
- Integrations that improve but aren't required
```

</phase_scoping>

<cascade_rules>
Deterministic rules for when changes trigger other changes:

```yaml
add_entity:
  always:
    - Add permissions entry (use default_pattern from <defaults>)
    - Add to glossary if name isn't self-explanatory
  if_user_facing:
    - Add view or view_state to display it
  if_has_lifecycle:
    - Define states with transitions
    - Add behaviors for state transitions
  if_referenced_by_other_entity:
    - Add relation to referencing entity

add_behavior:
  always:
    - Define input fields
    - Define at least one error case
  if_creates_entity:
    - Ensure entity exists
  if_uses_external_service:
    - Add to integrations
  if_user_triggered:
    - Add to view actions
  if_modifies_entity:
    - Ensure entity has required fields

add_field_to_entity:
  always:
    - Update entity examples to include field
  if_field_used_in_behavior:
    - Update behavior input/output

remove_entity:
  always:
    - Remove from permissions
    - Remove from phases
    - Remove from glossary
  cascade:
    - Remove behaviors that only act on this entity
    - Remove views that only display this entity
    - Remove relations from other entities
    - Remove from integrations.used_by

rename:
  always:
    - Update all references across entire spec
    - Update glossary entry
```

</cascade_rules>

<output_format>

Size targets:

```yaml
MVP: 300-500 lines
Small: 500-700 lines
Medium: 700-1000 lines
Large: 1000-1300 lines
```

File location: `docs/product-spec.md`
</output_format>

<process_create>

## CREATE Mode

### 1. Read Template

```bash
cat .claude/templates/product-spec.md
```

### 2. Analyze User Input

Think through:

```yaml
product:
  - What is the user building? (name, category)
  - What problem does it solve?
  - Who is it for?

entities:
  - What nouns appear? (user, post, comment → entities)
  - What data must be stored?
  - What has lifecycle states?

behaviors:
  - What verbs appear? (create, search, delete → behaviors)
  - What can users do?
  - What does system do automatically?

context:
  - Platform? (web, mobile, desktop, CLI)
  - Framework mentioned?
  - Single-user or multi-user?
  - Free, paid, or freemium?
```

Then categorize each template section:

```yaml
provided: # User gave explicit detail
inferable: # Derive using <inference_rules>
missing_critical: # Must ask — blocks generation
missing_optional: # Apply <defaults>
```

Critical items (must ask if missing):

```yaml
- identity.summary # What is it?
- users.primary # Who is it for?
- meta.platform # Web? Mobile? Desktop?
- behaviors # What can users do? (minimum 3)
- entities # What data exists? (minimum 1)
```

### 3. Ask Questions (if missing_critical exists)

```
To generate your Product Spec, I need:

1. [Section]: [Question]
   Why: [How this affects downstream agents]
   Example: [Concrete answer]
```

Maximum 5 questions per round.

### 4. Generate Product Spec

```bash
mkdir -p docs
cp .claude/templates/product-spec.md docs/product-spec.md
```

Fill in order (respects dependencies):

1. meta, identity
2. users, invariants
3. entities (with examples)
4. behaviors (with input fields and errors)
5. permissions (entry per entity)
6. limits (concrete numbers)
7. integrations (if any external services)
8. views (states matching entity states)
9. design (apply defaults, customize personality)
10. policies, phases (use <phase_scoping>), decisions, open, glossary

### 5. Validate

Check each:

- [ ] Every principle has meaning + tradeoff
- [ ] Every entity has 2+ examples including edge case
- [ ] Every behavior has input fields and error cases
- [ ] Every error has message + recovery
- [ ] Permissions cover all entities
- [ ] Limits have concrete numbers (not placeholders)
- [ ] Phase 1 follows <phase_scoping> criteria

If validation fails: fix the issue, do not ask user.

### 6. Deliver

```
## Product Spec Created

Location: `docs/product-spec.md`

### Summary
- {N} entities: {names}
- {N} behaviors: {names}
- {N} views: {names}
- Phase 1: {goal}

### Assumptions Made
- {assumption 1}
- {assumption 2}

### Needs Review
- {section}: {why}
```

</process_create>

<process_update>

## UPDATE Mode

### 1. Read Existing Spec

```bash
cat docs/product-spec.md
```

Parse and remember:

- All entity names and their fields
- All behavior names and their connections
- All view names and their states
- Current phase assignments

### 2. Analyze Change Request

Think through:

```yaml
what:
  - What exactly is the user asking to change?
  - Is this add/modify/remove/rename?

scope:
  - Which section is primarily affected?
  - What other sections reference this? (use <cascade_rules>)

impact:
  - Does this change Phase 1 scope?
  - Does this introduce new external dependency?
  - Does this affect permissions model?
```

Classify:

```yaml
change_type: add | modify | remove | rename
primary_section: entities | behaviors | views | ...
cascades: [list from <cascade_rules>]
complexity: simple | complex
```

Simple = single field change, typo fix, message update
Complex = new entity, remove feature, rename, multi-section impact

### 3. Confirm Understanding (if complex)

For simple changes: proceed directly.

For complex changes: confirm:

```
I understand you want to: {change description}

This will:
- {primary change}
- {cascade 1}
- {cascade 2}

Proceed?
```

### 4. Apply Changes

Use targeted edits (not full rewrite).

Order by dependency:

- Adding: entity → behaviors → views → permissions
- Removing: views → behaviors → permissions → entity
- Renaming: all references in single pass

### 5. Apply Cascades

Follow <cascade_rules> deterministically.

Check each applicable rule and apply.

### 6. Validate

Check <quality_requirements> for affected sections.
If validation fails: fix the issue.

### 7. Update Metadata

```yaml
meta:
  version: # Increment patch (0.1 → 0.2)
  updated: # Today's date
```

Add to decisions (if significant):

```yaml
decisions:
  - id: "D-{next}"
    date: "{today}"
    context: "{user request}"
    decision: "{what changed}"
    why: "{from user or inferred}"
```

### 8. Deliver

```
## Product Spec Updated

Version: {old} → {new}

### Changes Made

**{change_type}:**
- {section}: {item}

### Cascades Applied
- {section}: {what was auto-updated}

### Verify
- {section}: {why it needs attention}
```

</process_update>

<examples>

**Example 1: Add entity**

User: "Add a Tag entity for organizing sources"

Think through:

```yaml
what: Add new entity "Tag"
scope: entities + permissions + maybe behaviors/views
impact: Probably Phase 2 (organization feature)
```

Apply <cascade_rules> for add_entity:

```yaml
always:
  - permissions: add Tag (create: auth, read/update/delete: owner)
  - glossary: add "Tag: Label for categorizing sources"
if_user_facing: yes
  - views: add tag selector to source_detail, or tag_list view
if_referenced_by_other_entity: yes (Source → Tag)
  - entities.Source.relations: add many_to_many to Tag
```

**Example 2: Simple modification**

User: "Change duplicate error message to 'You already saved this'"

Think through:

```yaml
what: Modify error message
scope: behaviors.paste_content.errors[DUPLICATE].message only
impact: None
complexity: simple
```

Action: Direct edit, no confirmation, no cascades.

</examples>
