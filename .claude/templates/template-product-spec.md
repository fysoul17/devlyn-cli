# Product Spec

> **Purpose**: Source of truth for WHAT to build and WHY.  
> **Usage**: Input for AI agents generating Feature Specs → Plans → Tasks → Code.  
> **Principle**: Define the WHAT and WHY. Downstream agents derive the HOW.

---

# 1. META

```yaml
meta:
  name: "{Product Name}"
  version: "{X.Y}"
  updated: "{YYYY-MM-DD}"
  status: "{draft | review | approved | implementing}"
  owner: "{decision maker}"

  platform:
    type: "{web | mobile | desktop | cli | backend}"
    framework: "{framework + version}"
```

---

# 2. IDENTITY

```yaml
identity:
  summary: "{X is a Y that does Z for W}"

  insight: "{Core belief that makes this viable — what do we believe that others don't?}"

  principles:
    # Guide ALL downstream decisions. Feature Specs apply these.
    - principle: "{name}"
      meaning: "{what this means in practice}"
      tradeoff: "{what we sacrifice}"

    # Common principles to consider:
    # - Optimistic UI (show result before server confirms)
    # - Keyboard-first (every action without mouse)
    # - Progressive disclosure (simple first, reveal complexity)
    # - Undo over confirm (reverse actions vs block with dialogs)
    # - Offline-capable (works without network)
    # - Responsive feedback (user knows state within 100ms)

  anti_goals:
    - "{what we will NOT build, even if users ask}"
```

---

# 3. USERS

```yaml
users:
  primary:
    who: "{description}"
    goals: ["{what they want to accomplish}"]
    pains: ["{current problems}"]
    context: "{when/where they use this}"
    capabilities:
      technical: "{novice | intermediate | expert}"
      domain: "{none | familiar | expert}"

  not_for:
    - "{who we don't serve, and why}"
```

---

# 4. INVARIANTS

> Rules that must NEVER break. Violations are bugs.

```yaml
invariants:
  - rule: "{invariant}"
    why: "{rationale}"

  # Common invariants:
  # - "Users cannot access other users' data"
  # - "All mutations require authentication"
  # - "User data is never permanently deleted without explicit request"
  # - "Secrets never appear in logs or API responses"
```

# 5. BEHAVIORS

> All actions in the system. Feature Specs derive implementation.

```yaml
behaviors:
  "{behavior_name}":
    purpose: "{what this accomplishes}"
    actor: "{user | system | schedule}"
    trigger: "{what initiates}"

    input:
      - name: "{name}"
        type: "{type}"
        required: "{true | false}"
        validation: "{rules}"

    outcome: "{what changes when successful}"

    rules: # business logic
      - "{rule}"

    errors:
      - when: "{condition}"
        error: "{code}"
        message: "{user-facing}"
        recovery: "{what user can do}"

    emits: ["{triggered behaviors or events}"] # optional
```

<details>
<summary>Behavior Examples</summary>

```yaml
paste_content:
  purpose: "Save content from clipboard to inbox"
  actor: user
  trigger: "Paste in drop zone or keyboard shortcut"

  input:
    - name: content
      type: string | file
      required: true
      validation: "Max 10MB"
    - name: space_id
      type: uuid
      required: false
      validation: "User's space"

  outcome: "Source created with status=pending"

  rules:
    - "Detect content type (URL, text, image, file)"
    - "If URL: check for duplicate"
    - "If duplicate: surface existing instead"

  errors:
    - when: "Clipboard empty"
      error: "EMPTY_CLIPBOARD"
      message: "Nothing to paste"
      recovery: "Copy content first"
    - when: "Exceeds limit"
      error: "TOO_LARGE"
      message: "Content exceeds 10MB"
      recovery: "Try smaller content"
    - when: "Duplicate URL"
      error: "DUPLICATE"
      message: "Already saved"
      recovery: "View existing"

  emits: [process_source]

process_source:
  purpose: "Extract content and generate embedding"
  actor: system
  trigger: "Source created with status=pending"

  input:
    - name: source_id
      type: uuid
      required: true

  outcome: "Source has content, embedding, status=complete"

  rules:
    - "URL: fetch and extract main content"
    - "YouTube: extract transcript"
    - "Image: OCR"
    - "Timeout: 60s"

  errors:
    - when: "URL unreachable"
      error: "UNREACHABLE"
      message: "Couldn't reach URL"
      recovery: "Check link and retry"
    - when: "Extraction failed"
      error: "EXTRACTION_FAILED"
      message: "Couldn't extract content"
      recovery: "Try different content"

search:
  purpose: "Find sources by semantic similarity"
  actor: user
  trigger: "User enters query"

  input:
    - name: query
      type: string
      required: true
      validation: "1-500 chars"
    - name: space_id
      type: uuid
      required: false

  outcome: "Ranked list of matching sources (max 20)"

  rules:
    - "Generate query embedding"
    - "Vector similarity against user's sources"
    - "Only status=complete sources"

  errors:
    - when: "Query too short"
      error: "QUERY_SHORT"
      message: "Enter a few more words"
      recovery: "Add detail"
```

</details>

---

# 6. PERMISSIONS

> Who can do what. Business rules, not implementation.

```yaml
permissions:
  "{Entity}":
    create: "{who}"
    read: "{who}"
    update: "{who}"
    delete: "{who}"

  # "who" examples:
  # - "authenticated" (any logged-in user)
  # - "owner" (created/owns the resource)
  # - "owner + invited" (shared access)
  # - "admin" (admin role only)
  # - "public" (no auth required)
```

Example:

```yaml
permissions:
  Source:
    create: authenticated
    read: owner
    update: owner
    delete: owner

  Space:
    create: authenticated
    read: owner
    update: owner
    delete: owner
```

---

# 7. LIMITS

> Business constraints and quotas.

```yaml
limits:
  tiers:
    "{tier_name}":
      "{resource}": "{limit}"
      price: "{price}" # if paid

  on_limit: "{block | upgrade_prompt | soft_warning}"

  # Per-action limits (if different from tier)
  actions:
    "{behavior}": "{limit per time}"
```

Example:

```yaml
limits:
  tiers:
    free:
      sources: 100
      storage: "100MB"
      ai_queries: "50/month"

    pro:
      sources: unlimited
      storage: "10GB"
      ai_queries: unlimited
      price: "$10/month"

  on_limit: upgrade_prompt

  actions:
    process_source: "10/minute" # rate limit
```

---

# 8. INTEGRATIONS

> External services we depend on.

```yaml
integrations:
  "{service}":
    purpose: "{why we use this}"
    used_by: ["{behavior}"]
    fallback: "{what happens if unavailable}" # optional
```

Example:

```yaml
integrations:
  openai:
    purpose: "Embeddings (text-embedding-3-small) and chat (gpt-4)"
    used_by: [process_source, chat_with_sources]
    fallback: "Queue for retry, show 'AI temporarily unavailable'"

  youtube_transcript:
    purpose: "Extract video transcripts"
    used_by: [process_source]
    fallback: "Index title/description only"

  readability:
    purpose: "Extract article content from URLs"
    used_by: [process_source]
```

---

# 9. VIEWS

> UI surfaces and their states.

```yaml
views:
  "{view_name}":
    purpose: "{what user does here}"
    route: "{path}"

    states:
      "{state}":
        when: "{condition}"
        shows: ["{elements}"]

    data: ["{Entity}"]
    actions: ["{behavior}"]
```

Example:

```yaml
views:
  home:
    purpose: "Capture content and browse sources"
    route: "/"

    states:
      empty:
        when: "No sources"
        shows: [drop_zone, onboarding_hint]
      has_content:
        when: "Has sources"
        shows: [drop_zone, source_list, chat_input]
      viewing_source:
        when: "Source selected"
        shows: [source_list, source_detail_panel]

    data: [Source, Space]
    actions: [paste_content, search, view_source, delete_source]

  source_detail:
    purpose: "View and interact with single source"
    route: "/source/:id"

    states:
      loading:
        when: "Data loading"
        shows: [skeleton]
      processing:
        when: "status=pending|processing"
        shows: [header, processing_indicator]
      ready:
        when: "status=complete"
        shows: [header, content, chat]
      failed:
        when: "status=failed"
        shows: [header, error_state, retry_button]

    data: [Source, ChatMessage]
    actions: [chat_with_source, edit_source, delete_source]
```

---

# 10. DESIGN

> Visual and verbal direction. Feature Specs derive specifics.

```yaml
design:
  foundation:
    system: "{base system}" # e.g., "tailwind + shadcn/ui"

  aesthetic:
    personality: ["{adjective}", "{adjective}", "{adjective}"]
    inspiration:
      - source: "{reference}"
        take: "{what to learn}"
    avoid:
      - "{anti-pattern}"
    signature:
      - "{distinctive element}"

  patterns:
    # UX conventions — Feature Specs apply these
    list_order: "{newest_first | oldest_first | manual}"
    new_items: "{prepend | append}"
    empty_states: "{illustration | minimal | action-focused}"
    loading: "{skeleton | spinner}"
    optimistic: "{true | false}"
    detail_view: "{panel | page | modal}"
    destructive_actions: "{undo | confirm}"
    density: "{compact | comfortable | spacious}"

  voice:
    tone: ["{adjective}", "{adjective}"]
    formality: "{formal | conversational | casual}"
    patterns:
      success: "{how to say it}"
      error: "{how to say it}"
      empty: "{how to say it}"
    vocabulary:
      prefer: ["{word}"]
      avoid: ["{word}"]
```

<details>
<summary>Full Design Example</summary>

```yaml
design:
  foundation:
    system: "tailwind + shadcn/ui"

  aesthetic:
    personality: ["calm", "focused", "intelligent"]
    inspiration:
      - source: "Linear"
        take: "command palette, keyboard-first"
      - source: "Notion"
        take: "content-focused, subtle interactions"
      - source: "Arc"
        take: "spatial organization"
    avoid:
      - "generic SaaS gradients"
      - "stock illustrations"
      - "modal overload"
      - "hamburger menus on desktop"
    signature:
      - "command palette as primary nav"
      - "persistent AI chat sidebar"
      - "monospace for metadata"

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
    tone: ["helpful", "concise"]
    formality: conversational
    patterns:
      success: "Brief, no exclamation"
      error: "Cause + fix. No apology."
      empty: "What's missing + one action"
    vocabulary:
      prefer: [save, source, space]
      avoid: [submit, item, folder, oops, please]
```

</details>

---

# 11. POLICIES

> Cross-cutting requirements.

```yaml
policies:
  auth:
    method: "{session | jwt | oauth}"
    providers: ["{provider}"]

  privacy:
    data_export: "{yes | no}"
    data_deletion: "{soft | hard | on_request}"

  i18n:
    default: "{locale}"
    supported: ["{locale}"]

  accessibility:
    standard: "{WCAG 2.1 AA | none}"
```

---

# 12. PHASES

> What's in each release.

```yaml
phases:
  "{n}":
    name: "{name}"
    goal: "{what users can do after}"

    includes:
      entities: ["{name}"]
      behaviors: ["{name}"]
      views: ["{name}"]

    excludes:
      - what: "{deferred}"
        why: "{reason}"

    success: "{measurable outcome}"
```

Example:

```yaml
phases:
  1:
    name: "Core Capture"
    goal: "Save URLs/text, view, search"

    includes:
      entities: [User, Source]
      behaviors: [paste_content, process_source, search, delete_source]
      views: [home, source_detail]

    excludes:
      - what: "AI chat"
        why: "Capture loop first"
      - what: "Spaces"
        why: "Inbox-only simplifies UX"

    success: "Save URL → find via search in <30s"
```

---

# 13. DECISIONS

> What was decided and WHY.

```yaml
decisions:
  - id: "D-{n}"
    date: "{YYYY-MM-DD}"
    context: "{what question arose}"
    decision: "{what was decided}"
    why: "{reasoning}"
    implications: ["{consequence}"]
    revisit: "{when to reconsider}"
```

Example:

```yaml
decisions:
  - id: "D-001"
    date: "2024-01-15"
    context: "Users want shared spaces for teams"
    decision: "Single-user only for v1"
    why: |
      Collaboration adds complexity (permissions, sync, conflicts).
      Core value is personal knowledge management.
      Teams can layer on once core is solid.
    implications:
      - "No sharing UI"
      - "Simpler permissions"
    revisit: "Post-launch based on feedback"
```

---

# 14. OPEN

> Undecided items.

```yaml
open:
  - id: "Q-{n}"
    question: "{decision needed}"
    options:
      - "{option}: {tradeoff}"
    blocks: ["{what can't proceed}"]
    owner: "{who decides}"
    deadline: "{when}"
```

---

# 15. GLOSSARY

> Precise definitions.

```yaml
glossary:
  "{Term}": "{definition in this product's context}"
```

Example:

```yaml
glossary:
  Source: "Content saved by user (URL, note, file, etc.)"
  Space: "User-created container for organizing sources"
  Inbox: "Default location for new sources before organized"
```

---

# Validation Checklist

Before generating Feature Specs:

- [ ] Principles cover key UX decisions (optimistic? keyboard? undo vs confirm?)
- [ ] Every entity has complete fields and examples
- [ ] Every behavior has outcome and errors defined
- [ ] Permissions cover all entities
- [ ] Limits define tier boundaries
- [ ] Integrations list all external dependencies
- [ ] Design patterns answer: loading? new items? destructive actions?
- [ ] Decisions explain WHY, not just WHAT
- [ ] No [TBD] — move to Open Questions

---

# Size Guide

| Complexity | Lines     |
| ---------- | --------- |
| MVP        | 300-500   |
| Small      | 500-700   |
| Medium     | 700-1000  |
| Large      | 1000-1300 |

Over 1300 lines → split into Core + Domain specs.

---

# Derivation Reference

| Product Spec             | → Feature Spec Derives        |
| ------------------------ | ----------------------------- |
| Entity fields            | Schema, types, validators     |
| Entity examples          | Test fixtures                 |
| Behavior outcome + rules | Logic, sequences              |
| Behavior errors          | Error handling, UI feedback   |
| Permissions              | Auth middleware               |
| Limits                   | Quota checks, upgrade prompts |
| Integrations             | API clients, fallbacks        |
| View states              | Components, routing           |
| Design patterns          | Layout, interactions, loading |
| Voice                    | Copy, messages                |
