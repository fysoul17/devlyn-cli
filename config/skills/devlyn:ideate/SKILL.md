---
name: devlyn:ideate
description: Transforms unstructured ideas into implementation-ready planning documents through structured brainstorming, research, and a built-in self-skeptical rubric pass. Produces a three-layer document architecture (Vision, Roadmap index, auto-resolve-ready specs) to eliminate context pollution in the implementation pipeline. Default `--engine auto` routes the CHALLENGE rubric pass to OpenAI Codex (GPT-5.4) as a cross-model critic for a GAN dynamic. Use when the user wants to brainstorm, plan a new project or feature set, create a vision and roadmap, or structure scattered ideas into an actionable plan. Triggers on "let's brainstorm", "let's plan", "ideate", "I have an idea for", "help me think through", "let's explore", new project planning, feature discovery, roadmap creation, or when the user is throwing ideas that need structuring.
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

## Arguments

Parse these from the user's invocation message:

- `--engine MODE` (auto) — controls which model handles each ideation phase. Modes:
  - `auto` (default): Claude handles FRAME/EXPLORE/CONVERGE/DOCUMENT (ambiguous intent, writing quality), Codex runs the CHALLENGE rubric pass as critic (GAN dynamic). Requires Codex MCP server.
  - `codex`: Codex handles FRAME/EXPLORE/CONVERGE/DOCUMENT, Claude runs CHALLENGE (role reversal — builder and critic are always different models).
  - `claude`: all phases use Claude. No Codex calls.

**Engine pre-flight** (runs unless `--engine claude` was explicitly passed):
- The default engine is `auto`. If the user did not pass `--engine`, the engine is `auto` — not `claude`.
- Call `mcp__codex-cli__ping` to verify the Codex MCP server is available. If ping fails, warn the user and offer: [1] Continue with `--engine claude`, [2] Abort.
- Read `references/challenge-rubric.md` up front. The engine routing table lives in the auto-resolve skill's `references/engine-routing.md` under "Pipeline Phase Routing (ideate)" — read that on demand when routing decisions are needed.

**Consolidated flag**: `--with-codex` was rolled into the smarter `--engine auto` default. If the user passes it, inform them once and proceed with `--engine auto`: "Note: `--with-codex` was consolidated into `--engine auto` (default), which routes the CHALLENGE rubric pass to Codex automatically. No flag needed. Continuing with `--engine auto`."

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
3. **Run the Archive Pass** (see Context Archiving below) before summarizing. Summarizing a stale roadmap to the user wastes the exchange — they'll see "Phase 1 has 4 items" when really all 4 are already Done and the phase should be collapsed.
4. Summarize your understanding: "Here's what exists: [phases, item count, current status]. You want to add [new area]. Does this expand an existing phase or warrant a new one?"

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

In Replan mode: read existing docs first, **run the Archive Pass** (see Context Archiving below) before any reprioritization — you can't sensibly reorder work that's already finished — then focus on the Converge phase to reprioritize what remains. The Archive Pass also surfaces Backlog items whose Revisit date has passed, which are natural candidates when replanning.

### Quick Add Mode Detail

Quick Add is for when the user has a single concrete idea, bug report, or improvement — they don't need a full ideation session, just a new entry in the roadmap. This is the most common trigger for misuse: the request looks like a simple fix, so the temptation is to implement it. Don't. Capture it.

**On entry:**
1. Read `docs/ROADMAP.md` and relevant phase `_overview.md` files
2. **Run the Archive Pass first** (see Context Archiving below). Do this *before* you figure out where the new item goes — a stale roadmap will mislead phase selection and ID numbering. If the pass moves a phase out of the active section, the new item's natural home may change.
3. Identify the best-fit phase for the new item (or suggest a new phase if it doesn't fit)
4. Determine the next available item ID (e.g., if phase 2 has 2.1-2.4, the new item is 2.5)

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

ROADMAP.md is the tactical index. Every row that isn't Planned / In Progress / Blocked is noise — it dilutes attention, pads the file past its 150-line target, and makes future ideation sessions read stale context they'll have to mentally filter out. Done work should move; it shouldn't disappear.

The goal state: the active section of ROADMAP.md only lists work that still needs doing. Everything completed lives under a collapsed `## Completed` block at the bottom. Item spec files themselves stay in place — they remain on disk at `docs/roadmap/phase-N/{id}.md` because other specs may reference them — only the index row moves.

#### The Archive Pass

Run this at the start of every Quick Add, Expand, and Replan session (each mode's "On entry" checklist tells you when). It's deterministic and cheap. Never skip it to "save time" — the time you save by skipping it is immediately spent by you and the user arguing about a roadmap that shows phantom work.

1. **Read `docs/ROADMAP.md`.** For each phase, look at the Status column of every row.
2. **For each phase where every row is `Done`:** archive the whole phase.
   - Cut the phase's `## Phase N: …` heading and table out of the active section.
   - If no `## Completed` section exists yet at the bottom of the file, create one.
   - Add a `<details>` block inside Completed for this phase (see format below). Use the latest completion date you can find in the item spec frontmatter (`completed:` field, or today's date if absent). Item count is the row count.
3. **For individual `Done` rows inside an otherwise-active phase:** leave them in place. A row only moves when its whole phase is finished. (Mixed-state phases stay mixed so the user can see recent wins alongside open work.)
4. **Scan the Backlog table.** Surface any row whose "Revisit" date has passed — mention it to the user as a replan candidate. Don't auto-promote it; that's a conversation.
5. **Scan `docs/roadmap/decisions/`.** Flag any decision whose status is `accepted` but whose reasoning is visibly contradicted by the work that's now Done. Don't silently edit decisions; raise them as open questions.
6. **Report what you did.** Before moving on to the mode's main work, tell the user in one short paragraph: "Archived Phase 1 (3 items). Active roadmap is now Phase 2 (2 items). Proceeding with [Quick Add / Expand / Replan]." Skip the report only if nothing changed.

**Completed block format** (place at the bottom of ROADMAP.md, below Decisions):

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

If the `## Completed` section already exists and you're archiving an additional phase, append a new `<details>` block — don't rewrite existing ones.

#### Outdated decisions

When a decision becomes wrong because the world changed under it:
- Don't delete it — set its `status:` to `superseded` in the decision file's frontmatter and add a one-line pointer to the replacement decision record.
- This preserves the reasoning history for future reference, which matters more than a tidy decisions table.

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

<use_parallel_tool_calls>
EXPLORE often needs several independent lookups: web search for prior art, doc fetches, repo greps for existing patterns. When tool calls have no dependencies on each other, issue them in parallel in the same response. Spawn subagents in parallel when fanning out across distinct research topics. Only chain calls that depend on a previous call's output. Pace research across turns rather than front-loading every lookup before the user has framed direction — EXPLORE is dialogue-driven, parallel is just for the lookups inside any single turn.
</use_parallel_tool_calls>

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

### Internal draft — do not show the user yet

At this point you have an internal convergence draft: themes, phases, items, decisions. **Do not present it to the user yet.** Phase 3.5 CHALLENGE runs next, and the user will see exactly one summary — the post-challenge plan, with visibility into what CHALLENGE changed. Showing the pre-challenge draft first and then changing it after challenge creates a two-round confirmation loop that burns the user's trust.

## Phase 3.5: CHALLENGE

<phase_goal>Apply a strict 5-axis rubric to the internal convergence draft, then present one post-challenge summary to the user for confirmation. Always runs.</phase_goal>

<thinking_effort>
Engage maximum thinking effort here — both the solo rubric pass and, if enabled, the Codex pass. Use extended thinking ("ultrathink") when reading each item, applying each axis, and producing revisions. The default Claude failure mode in self-review is nodding along to the draft you just produced; shallow thinking here is the exact pattern this phase exists to prevent.

Before finalizing the rubric pass, verify your findings against the rubric one more time: every flagged item should have a specific Quote, a failing axis, and a concrete revision — not a vague concern.
</thinking_effort>

The user has been burned by plans that look good on the surface but fall apart under scrutiny. Every time they accept a plan and then ask "is this no-workaround, no-guesswork, no-overengineering, world-class best practice, optimized?" the honest answer is almost always no. This phase makes that the *default* behavior — the plan challenges itself before the user has to.

### The rubric — single source of truth

Read `references/challenge-rubric.md` before starting. That file is the only definition of the 5 axes, the finding format, the hard rule about respecting explicit user intent, and the good-vs-bad examples. Both the solo pass and the Codex pass use the same rubric; do not re-derive it inline.

### Solo pass (always runs)

Apply the rubric to the internal convergence draft. Produce findings in the format specified in `challenge-rubric.md` (Severity / Quote / Axis / Why / Fix).

For Quick Add with one new item, one solo pass is enough. For a full greenfield or expand plan, run the rubric once, revise, and run it again on the revision. If a third pass would be needed, the plan has structural problems that belong in the user-facing summary as open questions — surface them rather than iterating further.

If the plan came from one model in one pass, it almost always fails at least one axis somewhere. Nodding along to your own draft defeats the entire point of the phase.

### Codex critic pass (engine-routed)

**If `--engine auto`** (default): Codex runs the CHALLENGE rubric pass automatically as critic.

Call `mcp__codex-cli__codex` with `model: "gpt-5.4"`, `reasoningEffort: "xhigh"`, `sandbox: "read-only"`, `workingDirectory: <project root>`. The `prompt` parameter is built from the packaged plan + the inlined rubric + the appended Codex instructions. Codex has no filesystem access to this project, so everything it needs travels in the prompt.

**Step 1 — Package the post-solo plan.** Build the prompt with these sections in this order:

```
## Problem framing (from FRAME phase)
[problem statement, constraints, success criteria, anti-goals]

## Confirmed facts vs assumptions
Confirmed by user: [list each fact the user explicitly confirmed]
Assumptions (not yet confirmed): [list each assumption the agent made]

## Plan (post-solo-CHALLENGE)
Vision: [one sentence]
Phase 1 ([theme]): [items with one-line descriptions and dependencies]
Phase 2 ([theme]): ...
Architecture decisions: [each with what / why / alternatives considered]
Deferred to backlog: [items + reason]

## Findings from the solo rubric pass
[list each with: severity, axis, quote, why, fix, whether applied]

## Rubric
[INLINE the full text of references/challenge-rubric.md here verbatim — Codex needs the rubric definition in the prompt itself]

## Your job
You are applying an independent rubric pass to the PLANNING document above. This is a roadmap, not code — judge the shape of the plan, not implementation details. The user explicitly asked to be challenged because soft-pedaled plans waste their time.

You are running AFTER a solo pass by Claude. Catch what the solo pass missed; do not just agree with what it already caught. For each existing solo finding, reply either "confirmed" (with one-line agreement) or "I would frame this differently" (with a reason). Then add your own findings that the solo pass missed.

Use the finding format from the rubric above: Severity / Quote / Axis / Why / Fix. The Quote field is load-bearing — anchor each finding to a specific line from the plan.

Respect explicit user intent. If the user confirmed something in the "Confirmed facts" section, the rubric does not override it silently. Raise the conflict as a note and let the orchestrator surface it to the user.

End with a verdict: PASS / PASS WITH MINOR FIXES / FAIL — REVISION REQUIRED, plus a one-line explanation.
```

**Step 2 — Reconcile.** Merge the two finding lists:
- Same finding from both → keep the more specific wording, mark "confirmed by both"
- Codex-only → prefix `[codex]` in internal notes so the user-facing summary can attribute correctly
- Solo-only → keep as-is
- Conflicts (solo says X, Codex says not-X) → record both, do not silently pick one; if material, surface as an open question in the user-facing summary

If Codex raised CRITICAL or HIGH findings the solo pass missed, apply the fixes to the plan before presenting the user-facing summary — unless fixing would change something the user explicitly confirmed, in which case follow the rubric's "Respect explicit user intent" rule.

**Do not loop.** One Codex pass is enough. If the result is still FAIL after reconciliation, the plan has structural problems that belong in the user-facing summary as open questions rather than further iteration.

**If `--engine codex`**: Role reversal — Codex built the plan, so Claude runs the solo CHALLENGE pass and that is the only pass. Do not also run Codex on CHALLENGE — builder and critic should always be different models. Skip this section.

**If `--engine claude`**: No Codex calls. The solo pass is the only pass.

### Respect explicit user intent

The rubric is a quality lens, not an override. If a finding conflicts with something the user explicitly and clearly asked for, follow the "Hard rule" section in `challenge-rubric.md`: record the finding, **do not silently rewrite the plan**, and surface it as an open question in the summary below. The user makes the call.

### User-facing summary (the first and only time the user sees the plan)

After the rubric pass(es), present the post-challenge plan to the user for confirmation. This is the first time the user sees the converged plan — by design, so they see a rubric-checked result rather than a draft that immediately gets revised.

Format:
```
Vision: [one sentence]
Phases: [N] phases, [M] total items
Phase 1 ([theme]): [items with brief descriptions]
Phase 2 ([theme]): [items]
Key decisions: [list]
Deferred: [items with reasons]

## CHALLENGE results

Solo pass: [N findings, M applied]
Codex pass: [N findings, M applied]   ← only on --engine auto

Changes applied during CHALLENGE:
- [item]: [what changed and which axis triggered it]

Open questions for you (rubric flagged something you explicitly asked for):
- [item]: rubric says [finding]; you asked for [original]; here is the tradeoff — proceed as-is, or adopt the alternative?
```

Get explicit confirmation before proceeding to DOCUMENT.

### Quick Add mode

For single-item additions, run one solo rubric pass on just the new item. Even then do not skip — single-item additions are exactly where overengineering and workarounds slip in unnoticed, because the lack of surrounding context makes a bad item look self-contained and harmless.

## Engine Routing for FRAME / EXPLORE / CONVERGE / DOCUMENT

**If `--engine codex`**: Phases 1-3 and Phase 4 are delegated to Codex. For each phase, call `mcp__codex-cli__codex` with `model: "gpt-5.4"`, `reasoningEffort: "xhigh"`, `sandbox: "workspace-write"`, and the phase instructions + user context as the prompt. Use `sessionId` to maintain conversational context across phases (note: sandbox/fullAuto only apply on the first call). Claude remains the orchestrator — it reads Codex's output, manages the conversation with the user (confirmation prompts, clarifying questions), and routes findings between phases.

**If `--engine auto` or `--engine claude`**: All planning phases use Claude directly (current behavior). Claude's ambiguous intent handling and writing quality benchmarks favor it for planning tasks.

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
- [ ] CHALLENGE ran against `references/challenge-rubric.md` (solo, plus Codex critic on `--engine auto`); no item still fails any axis at CRITICAL or HIGH severity
- [ ] User saw the post-challenge plan as the first and only confirmation prompt — no pre-challenge draft was shown first
- [ ] Any rubric finding that conflicted with explicit user intent was surfaced as an open question, not silently applied

## Language

Generate all documents in the language the user communicates in. If the user mixes languages, match their primary language for prose and keep technical terms in English.
