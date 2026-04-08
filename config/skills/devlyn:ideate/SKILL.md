---
name: devlyn:ideate
description: Transform unstructured ideas into implementation-ready planning documents through structured brainstorming, research, and multi-perspective synthesis. Produces a three-layer document architecture (Vision, Roadmap index, auto-resolve-ready specs) that eliminates context pollution in the implementation pipeline. Use when the user wants to brainstorm, plan a new project or feature set, explore possibilities, create a vision and roadmap, or structure scattered ideas into an actionable plan. Triggers on "let's brainstorm", "let's plan", "ideate", "I have an idea for", "help me think through", "let's explore", new project planning, feature discovery, roadmap creation, or when the user is throwing ideas that need structuring. Also triggers when the user shares links or resources for a new initiative and needs them synthesized into a plan, or wants to update an existing roadmap with new ideas.
---

# Ideation to Implementation Bridge

Turn unstructured thinking into auto-resolve-ready documents. The output is a precision-engineered context pipeline — each document layer serves a specific role so that implementation agents receive exactly the context they need, nothing more.

<hard_boundary>
This skill is a PLANNING tool, not an IMPLEMENTATION tool. Your output is documents (VISION.md, ROADMAP.md, item specs) — never code changes.

When the user describes a bug, improvement, or feature request through ideate, they want it CAPTURED in the roadmap, not FIXED in the codebase. Even if the fix seems trivial and obvious, resist the urge to implement it. The user chose `/devlyn:ideate` over `/devlyn:resolve` for a reason — they want planning, not coding.

Concretely:
- Do NOT read source code to find and fix issues
- Do NOT edit application files (.tsx, .ts, .py, .js, etc.)
- DO create or update roadmap documents (VISION.md, ROADMAP.md, item specs)
- DO explore and research the problem space to write better specs
- If you catch yourself about to open a source file to make a code change, stop — that's a signal you've left ideation mode
</hard_boundary>

<why_this_matters>
When ideas flow directly from conversation to `/devlyn:auto-resolve`, context degrades at each handoff:
- Abstract vision statements cause over-engineering (the agent optimizes for principles instead of deliverables)
- Full roadmaps create attention noise (49 irrelevant items dilute focus on item #3)
- Done criteria generated from vague prompts miss the user's actual intent

This skill solves the context engineering problem by producing **self-contained specs** — each carries just enough context for auto-resolve to work autonomously.
</why_this_matters>

## Output Architecture

The skill produces a three-layer progressive disclosure structure:

```
docs/
├── VISION.md              # Layer 1: Strategic WHY (~50-100 lines)
│                          # Orientation only. auto-resolve never reads this.
│
├── ROADMAP.md             # Layer 2: Tactical index (what, in what order)
│                          # Thin table linking to detail specs. auto-resolve never reads this.
│
└── roadmap/               # Layer 3: Auto-resolve-ready specs
    ├── phase-1/
    │   ├── _overview.md   # Phase-level context and goals
    │   ├── 1.1-xxx.md     # Self-contained spec → direct auto-resolve input
    │   └── 1.2-yyy.md
    ├── phase-2/
    │   └── ...
    ├── decisions/         # Architecture decision records (why we chose X over Y)
    │   └── 001-xxx.md
    └── backlog/           # Ideas acknowledged but not yet phased
        └── ...
```

**Core principle**: auto-resolve reads ONE spec file. That file is self-contained. Vision and Roadmap exist for humans and for this ideation skill — not for the implementation pipeline.

Read `references/templates/` for the exact format of each document type when generating output.

## Conversation Protocol

Ideation is a dialogue, not a monologue. The user will come in with scattered ideas, incomplete thoughts, and implicit assumptions. Your job is to draw out accurate, complete information through back-and-forth conversation — not to fill gaps with guesses.

<conversation_rhythm>
**Ask, don't assume.** When information is missing or ambiguous, ask targeted questions. Generating a spec with wrong assumptions is worse than asking one more question. The user wants accuracy (documents they can trust and hand to auto-resolve), not speed.

**2-3 questions at a time, max.** Don't dump a 10-item questionnaire. Ask the most important unknowns, get answers, then ask the next batch based on what you learned. Each exchange should build on the last.

**Summarize after each exchange.** After the user shares information, reflect it back concisely: "So what I'm hearing is [X]. Is that right, or am I missing something?" This catches misunderstandings early — much cheaper than rewriting specs later.

**Confirm before phase transitions.** Before moving from FRAME → EXPLORE, or EXPLORE → CONVERGE, summarize the current state and ask if the user is ready to move on. Never silently transition.

**Capture energy, then clarify.** When the user is excited and throwing out rapid-fire ideas, don't interrupt the flow with structural questions. Let them finish, capture everything, then come back with targeted clarifications: "Love these ideas. A few things I want to make sure I get right: [questions]."

**Track what's confirmed vs. assumed.** Mentally separate facts the user stated from inferences you made. When generating documents, only write confirmed facts. Flag assumptions explicitly: "I'm assuming [X] based on [Y] — correct?"
</conversation_rhythm>

## Detecting the Mode

Before starting, identify what the user needs:

| Signal | Mode | Approach |
|--------|------|----------|
| No existing docs, new project or idea | **Greenfield** | Full flow: Frame → Explore → Converge → Document |
| Existing docs, user adds new ideas | **Expand** | Lighter Frame, focused Explore on new area, merge into existing phases |
| Existing docs, user describes a single bug/improvement/idea | **Quick Add** | Read existing roadmap, create one item spec, add row to ROADMAP.md |
| One specific feature needs deep thought | **Deep-dive** | Intensive Explore on one topic, output 1-3 specs |
| User shares links/resources to process | **Research-first** | Lead with Explore (research synthesis), then standard flow |
| Existing roadmap, user wants to reprioritize | **Replan** | Read existing docs, focus on Converge, update documents |

Announce the detected mode and confirm before proceeding.

### Expand Mode Detail

Expand is the most common mode after initial setup — the user already has Vision + Roadmap and wants to add new capabilities. This mode requires careful integration with existing documents.

**On entry:**
1. Read `docs/VISION.md`, `docs/ROADMAP.md`, and existing phase `_overview.md` files to understand the established context
2. Scan existing item specs to understand what's built and what's planned
3. Summarize your understanding: "Here's what exists: [phases, item count, current status]. You want to add [new area]. Does this expand an existing phase or warrant a new one?"

**During ideation:**
- FRAME is lighter — the vision already exists, focus on framing the NEW area only
- EXPLORE focuses specifically on the new capability and how it integrates with existing features
- CONVERGE must consider dependencies on existing items, not just new ones

**During document generation:**
- Don't overwrite existing VISION.md unless the user explicitly wants to update it
- Continue numbering from existing IDs (if Phase 2 exists with 2.1-2.4, new items start at 2.5 or create Phase 3)
- Add new rows to ROADMAP.md, don't regenerate the whole table
- New item specs can reference existing items in their Dependencies section
- If new items change the meaning of existing items, flag this: "Adding [X] may affect the scope of existing item [Y]. Should we update [Y]'s spec?"

In Replan mode, also read existing docs first, then focus on the Converge phase to reprioritize.

### Quick Add Mode Detail

Quick Add is for when the user has a single concrete idea, bug report, or improvement — they don't need a full ideation session, just a new entry in the roadmap. This is the most common trigger for misuse: the request looks like a simple fix, so the temptation is to implement it. Don't. Capture it.

**On entry:**
1. Read `docs/ROADMAP.md` and relevant phase `_overview.md` files
2. Identify the best-fit phase for the new item (or suggest a new phase if it doesn't fit)
3. Determine the next available item ID (e.g., if phase 2 has 2.1-2.4, the new item is 2.5)

**Workflow (minimal — no full Frame/Explore/Converge):**
1. Confirm the idea with the user: "I'll add this as [item title] in Phase [N]. That sound right?"
2. Ask 1-2 clarifying questions if the requirement is unclear (skip if the user gave enough detail)
3. Generate the item spec following `references/templates/item-spec.md`
4. Add a row to `docs/ROADMAP.md`
5. Output confirmation: the file path and a suggested auto-resolve command

**Example output:**
```
Added: docs/roadmap/phase-2/2.5-back-to-review-button.md

To implement:
/devlyn:auto-resolve "Implement per spec at docs/roadmap/phase-2/2.5-back-to-review-button.md"
```

### Context Archiving

As projects progress, completed work accumulates and dilutes the active roadmap. Archive stale context at these trigger points:

**When an entire phase is complete:**
1. Move the phase's table from the active section to a `## Completed` section at the bottom of ROADMAP.md
2. Keep it collapsed — just phase name, completion date, and item count
3. Item spec files stay in place (they're self-contained and may be referenced by dependencies)

```markdown
## Completed
<details>
<summary>Phase 1: Foundation (completed 2026-04-15, 4 items)</summary>

| # | Feature | Completed |
|---|---------|-----------|
| 1.1 | Auth & Onboarding | 2026-02-10 |
| 1.2 | Order Management | 2026-03-05 |
| 1.3 | Inventory Tracking | 2026-03-28 |
| 1.4 | Customer Directory | 2026-04-15 |
</details>
```

**When entering Expand or Replan mode:**
1. Scan ROADMAP.md for items marked Done — if all items in a phase are Done, archive that phase
2. Check Backlog for items whose "Revisit" date has passed — surface them as candidates for the new phase
3. Review decisions — flag any marked `accepted` that may need revisiting given new context

**When a decision becomes outdated:**
- Don't delete it — mark status as `superseded` and add a note pointing to the replacement decision
- This preserves the reasoning history for future reference

The goal: ROADMAP.md's active section should only show work that's planned, in-progress, or blocked. Everything else moves to Completed or gets re-evaluated.

## Phase 1: FRAME

<phase_goal>Establish problem space boundaries before exploring solutions.</phase_goal>

The biggest risk in ideation is premature convergence — jumping to solutions before understanding the problem. This phase prevents that.

Establish through conversation:
1. **Problem statement**: What problem or opportunity? For whom? Why now?
2. **Constraints**: What can't change? (tech stack, timeline, existing commitments)
3. **Success criteria**: How will we know this worked? (outcomes, not outputs)
4. **Anti-goals**: What are we explicitly NOT trying to do?

Adapt to what the user has already shared — if they came in with a clear vision, this might be a quick confirmation. If the idea is fuzzy, spend more time here. Ask conversationally, not as a rigid questionnaire.

Don't write documents yet. The output of this phase is a shared mental model between you and the user.

## Phase 2: EXPLORE

<phase_goal>Systematically expand the possibility space before narrowing it.</phase_goal>

This is the creative core — the phase that should take the most conversational turns. The user chose to ideate with AI because they want perspectives, research, and creative expansion they wouldn't get alone.

<research_protocol>
When relevant, actively research before and during brainstorming:
- **Existing solutions**: What's already out there? (web search, documentation)
- **Technical feasibility**: Can this be built within the constraints? Where are the hard parts?
- **Patterns and prior art**: How have similar problems been solved?
- **Market/user context**: Who else needs this? What do they currently use?

Not every ideation needs all of these — a personal side project doesn't need market research. Judge what's relevant and use subagents for parallel research when multiple topics need investigation.
</research_protocol>

<multi_perspective>
For each major idea, consider it from at least three angles:
- **User**: Is this actually useful? Does it solve a real pain?
- **Technical**: Is this buildable? Where are the complexity hotspots?
- **Strategic**: Does this align with the vision? Does it create leverage for future work?

Add perspectives as relevant:
- **Risk**: What could go wrong? What are the dependencies?
- **Business**: Does this create value? Is the effort justified?
- **Accessibility**: Is this inclusive? Who gets left out?
</multi_perspective>

<creative_expansion>
When the conversation needs energy or the user feels stuck:
- **"What if..."** — Remove a constraint and see what emerges
- **Analogy transfer** — "How does [adjacent domain] solve this?"
- **Inversion** — "What's the worst version? Now invert it."
- **10x thinking** — "If this needed 10x users, what changes?"
- **Minimum viable magic** — "What's the smallest thing that would feel magical?"

Use these naturally in conversation, not as a mechanical checklist.
</creative_expansion>

As ideas accumulate, periodically synthesize:
```
Here's where we are:
- Core ideas: [list]
- Open questions: [list]
- Tensions to resolve: [list]
- Research still needed: [list]
```

This prevents circular conversations and gives the user a clear sense of progress.

## Phase 3: CONVERGE

<phase_goal>Transform exploration into decisions.</phase_goal>

When the user signals readiness or exploration winds down naturally, shift to convergence.

### Theme Clustering
Group related ideas into coherent themes:
```
Theme A: [name]
- Ideas: 1, 3, 7
- Value: [why this matters]
- Risk: [what could go wrong]
```

### Prioritization
Use value x feasibility as the primary framework:
- **High value + High feasibility** → Phase 1 (build first)
- **High value + Low feasibility** → Phase 2+ (build after foundation exists)
- **Low value + High feasibility** → Backlog (if time permits)
- **Low value + Low feasibility** → Cut

Present as a recommendation — the user makes the final call on ordering.

### Sequencing
Within each phase:
- **Dependencies**: What must exist before what?
- **Risk ordering**: Build uncertain things first (fail fast)
- **Value delivery**: Each phase should deliver usable value, not just infrastructure

### Architecture Decisions
Surface decisions that affect multiple items — technology choices, data model, integration approaches, UX patterns. For each: **What** was decided, **Why** (tradeoffs), and **What alternatives** were considered. These become decision records.

### Confirmation
Before generating documents, present a final summary:
```
Vision: [one sentence]
Phases: [N] phases, [M] total items
Phase 1 ([theme]): [items with brief descriptions]
Phase 2 ([theme]): [items]
Key decisions: [list]
Deferred: [items with reasons]
```

Get explicit confirmation before proceeding to document generation.

## Phase 4: DOCUMENT

<phase_goal>Generate the three-layer document set.</phase_goal>

Read the templates before generating:
- `references/templates/vision.md` — VISION.md format
- `references/templates/roadmap.md` — ROADMAP.md index format
- `references/templates/item-spec.md` — Auto-resolve-ready spec format
- `references/templates/decision.md` — Architecture decision record format

### Generation Order
1. `docs/VISION.md` — from Phase 1 framing + Phase 3 decisions
2. `docs/roadmap/decisions/` — one file per architecture decision
3. `docs/roadmap/phase-N/_overview.md` — phase-level context
4. `docs/roadmap/phase-N/{id}-{name}.md` — one per roadmap item
5. `docs/ROADMAP.md` — index linking to everything above

### Item Spec Quality

Each Layer 3 spec is the direct input to auto-resolve. Its quality determines implementation quality.

<spec_quality_criteria>
**Requirements section** — becomes auto-resolve's done-criteria:
- Testable: a test can assert it OR a human can verify in under 30 seconds
- Specific: not "handles errors well" but "returns 400 with `{error: 'missing_field', field: 'email'}`"
- Scoped: tied to this item only, not aspirational

**Context section** — 2-3 sentences maximum. Just enough for auto-resolve to understand WHY without loading the full vision.

**Out of Scope** — explicitly states what this item does NOT do. This is what prevents auto-resolve from over-building, which is one of its most common failure modes.

**Constraints** — technical constraints with reasoning. Auto-resolve respects constraints significantly better when it understands the motivation behind them.
</spec_quality_criteria>

If an item is too vague to write specific requirements, it needs more exploration (revisit Phase 2 for that item) or should be split into smaller items.

### Handling Existing Documents
In **Expand** and **Replan** modes:
- Read existing documents first
- Merge new items into the existing phase structure
- Preserve existing items (don't overwrite or reorder without confirmation)
- Update ROADMAP.md index to include new entries

### Output Summary
After generating all documents:
```
Documents created:
- docs/VISION.md
- docs/ROADMAP.md
- docs/roadmap/phase-1/_overview.md
- docs/roadmap/phase-1/1.1-xxx.md
- docs/roadmap/phase-1/1.2-yyy.md
- docs/roadmap/decisions/001-xxx.md
[total: N files]
```

## Phase 5: BRIDGE

<phase_goal>Connect documents to the implementation pipeline.</phase_goal>

After document generation, output the implementation guide:

```
## Implementation

To implement each item:
/devlyn:auto-resolve "Implement per spec at docs/roadmap/phase-1/1.1-xxx.md — read the spec file for requirements, constraints, and scope boundaries"

Recommended order (respecting dependencies):
1. 1.1 [name] — no dependencies
2. 1.2 [name] — depends on 1.1
3. 1.3 [name] — depends on 1.1
...

After completing each item:
1. Update status in the item spec frontmatter (status: done)
2. Update ROADMAP.md status column
```

The auto-resolve prompt explicitly tells the build agent to read the spec file — this ensures done-criteria are adopted from the spec rather than generated from scratch, preserving the ideation context through to implementation.

## Quality Checklist

Before finalizing, verify:
- [ ] Every roadmap item has a linked spec file
- [ ] Every spec has testable requirements (not vague statements)
- [ ] Every spec has an Out of Scope section
- [ ] Every spec's Context section is 3 sentences or fewer
- [ ] ROADMAP.md is an index only — no inline specifications
- [ ] No spec requires reading VISION.md to be understood (self-contained)
- [ ] Dependencies between items are documented in both specs
- [ ] Architecture decisions include reasoning and alternatives considered

## Language

Generate all documents in the language the user communicates in. If the user mixes languages, match their primary language for prose and keep technical terms in English.
