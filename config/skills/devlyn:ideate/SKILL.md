---
name: devlyn:ideate
description: Transforms unstructured ideas into implementation-ready planning documents through structured brainstorming, research, and a built-in self-skeptical rubric pass. Produces a three-layer document architecture (Vision, Roadmap index, auto-resolve-ready specs) to eliminate context pollution in the implementation pipeline. Default `--engine auto` routes the CHALLENGE rubric pass to OpenAI Codex (GPT-5.5) as a cross-model critic for a GAN dynamic. Use when the user wants to brainstorm, plan a new project or feature set, create a vision and roadmap, or structure scattered ideas into an actionable plan. Triggers on "let's brainstorm", "let's plan", "ideate", "I have an idea for", "help me think through", "let's explore", new project planning, feature discovery, roadmap creation, or when the user is throwing ideas that need structuring.
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
  - `auto` (default): Claude handles FRAME/EXPLORE/CONVERGE/DOCUMENT (ambiguous intent, writing quality), Codex runs the CHALLENGE rubric pass as critic (GAN dynamic). Requires the local `codex` CLI on PATH; on failure the engine pre-flight silently downgrades to `claude` per `config/skills/_shared/engine-preflight.md`.
  - `codex`: Codex handles FRAME/EXPLORE/CONVERGE/DOCUMENT, Claude runs CHALLENGE (role reversal — builder and critic are always different models).
  - `claude`: all phases use Claude. No Codex calls.

**Engine pre-flight**: follow `config/skills/_shared/engine-preflight.md` — the one shared ping/downgrade rule every skill uses. Then read `references/challenge-rubric.md` up front.

**Consolidated flag**: `--with-codex` was rolled into the smarter `--engine auto` default. If the user passes it, inform them once and proceed with `--engine auto`: "Note: `--with-codex` was consolidated into `--engine auto` (default), which routes the CHALLENGE rubric pass to Codex automatically. No flag needed. Continuing with `--engine auto`."

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

**Tie-breaks when a request matches two modes:** choose the narrowest mode that satisfies the request. Quick Add wins over Expand when the user has one concrete item in mind. Research-first wins over Deep-dive when links or resources are the primary input. Deep-dive wins over Expand when one topic specifically needs depth. Replan is chosen only when priority or order changes are explicit. If two modes still look equally plausible after applying these rules, present the top two to the user and let them pick — silently choosing one wastes the session if the other was right.

Announce the detected mode and confirm before proceeding.

### Mode invariants (keep these regardless of which mode runs)

These are the rules that make modes safe. Violating one silently corrupts the roadmap; the detailed workflow for each mode lives in `references/modes.md` — read it when entering that mode.

- **Capture, don't fix.** Quick Add looks like a trivial bug report; never drift into implementation. The `<hard_boundary>` above applies to every mode.
- **Archive-before-summarize.** In Quick Add / Expand / Replan, run the Archive Pass *before* summarizing or choosing an ID when any phase in ROADMAP.md is entirely `Done`. Skip otherwise — on a fresh roadmap the pass is no-op bookkeeping. The Archive Pass edits ROADMAP.md only; item spec files stay at `docs/roadmap/phase-N/{id}.md` — never moved or deleted.
- **Numbering continuity.** Never renumber existing items. New items continue from the next available ID in the chosen phase (e.g., Phase 2 with 2.1-2.4 → new item is 2.5, or open Phase 3).
- **Don't overwrite established docs.** VISION.md is rewritten only on explicit user request. ROADMAP.md rows are appended, not regenerated. Existing item specs are never replaced without confirmation.
- **Flag spec impact.** If a new item changes the meaning of an existing item, surface it as a question — don't silently edit the older spec.
- **Superseded over deleted.** Decisions that became wrong get `status: superseded` + a pointer to the replacement; reasoning history is more valuable than a tidy table.

Full per-mode workflow (entry steps, conversation pattern, generation rules), the Archive Pass algorithm, and the Completed-block format are in `references/modes.md`.

## Phase 1: FRAME

<phase_goal>Establish problem space boundaries before exploring solutions.</phase_goal>

The biggest risk in ideation is premature convergence — jumping to solutions before understanding the problem. This phase prevents that.

Establish through conversation:
1. **Job-to-be-Done**: In one sentence — "When [situation], [user] wants to [motivation], so they can [outcome]." Capture this before anything else. If the user cannot produce it, that is itself the finding — pause and explore the situation until the sentence exists. A bare problem statement without this frame is a state description, not a job, and downstream specs built from it will describe system behavior instead of customer progress.
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
- **Evidence discipline**: Treat prior art as source-backed only when verified by a fetched link or documentation the user can open. If a pattern is inferred from memory or analogy, label it `[UNVERIFIED]` inline and do not present it as market fact. The CHALLENGE rubric's NO GUESSWORK axis fires hard on unlabeled claims that look authoritative but are actually recall.

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

### The rubric — single source of truth

Read `references/challenge-rubric.md` before starting. That file is the only definition of the 5 axes, the finding format, the hard rule about respecting explicit user intent, and the good-vs-bad examples. Both the solo pass and the Codex pass use the same rubric; do not re-derive it inline.

### Solo pass (always runs)

Apply the rubric to the internal convergence draft. Produce findings in the format specified in `challenge-rubric.md` (Severity / Quote / Axis / Why / Fix).

For Quick Add with one new item, one solo pass is enough. For a full greenfield or expand plan, run the rubric once, revise, and run it again on the revision. If a third pass would be needed, the plan has structural problems that belong in the user-facing summary as open questions — surface them rather than iterating further.

### Codex critic pass (engine-routed)

**If `--engine auto`** (default): Codex runs the CHALLENGE rubric pass automatically as critic.

Run `bash .claude/skills/_shared/codex-monitored.sh -C <project root> -s read-only -c model_reasoning_effort=xhigh "<inlined-prompt>"`. The wrapper closes stdin and emits a heartbeat every 30s on stderr so long Codex critique calls don't starve the outer API byte-watchdog (iter-0008 mechanism); full rationale in `_shared/codex-config.md`. The prompt is built from the packaged plan + the inlined rubric + the appended Codex instructions — Codex has no filesystem access under read-only, so everything it needs travels in the prompt. Omit `-m` to inherit the CLI flagship.

**Step 1 — Package the post-solo plan.** Build the prompt per `references/codex-critic-template.md` (section order, rubric inlining, Codex-specific instructions all live there verbatim — follow the template structure, fill in the plan/findings sections).

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

**If `--engine codex`**: Phases 1-3 and Phase 4 are delegated to Codex. For each phase, run `bash .claude/skills/_shared/codex-monitored.sh -C <project root> --full-auto -c model_reasoning_effort=xhigh "<phase prompt + user context>"`. The wrapper passes args through verbatim — flag semantics are unchanged; rationale in `_shared/codex-config.md`. For multi-phase continuity, use `bash .claude/skills/_shared/codex-monitored.sh resume --last` on subsequent phases so the session carries prior context. Claude remains the orchestrator — it reads Codex's stdout (heartbeat lines arrive on stderr as harness annotations, not Codex output), manages the conversation with the user (confirmation prompts, clarifying questions), and routes findings between phases.

**If `--engine auto` or `--engine claude`**: All planning phases use Claude directly (current behavior). Claude's ambiguous intent handling and writing quality benchmarks favor it for planning tasks.

## Phase 4: DOCUMENT

<phase_goal>Generate the three-layer document set.</phase_goal>

**Before writing any document, read `references/document-generation.md`.** It contains the template paths, generation order, Expand/Replan-mode merge rules, and the `<spec_quality_criteria>` that determine auto-resolve's downstream output quality — Requirements must be testable/specific/scoped, Context 2–3 sentences, Out of Scope explicit, Constraints paired with reasoning. Skipping these is the most common cause of vague specs and narrowed implementations.

**Post-write validation** (iter-0019.8 — applies to greenfield, Expand, Replan, Quick Add): immediately after writing each item spec at `docs/roadmap/phase-N/<id>-<name>.md`, validate the canonical verification carrier:

```
python3 .claude/skills/_shared/spec-verify-check.py --check docs/roadmap/phase-N/<id>-<name>.md
```

Exit 0 → proceed. Exit 2 → re-prompt yourself to fix the `## Verification` ` ```json ` block (the script's stderr line names the exact shape error: invalid JSON, empty `verification_commands` array, non-string `cmd`, bool `exit_code`, etc.). Re-write the spec, re-run the check, repeat until exit 0. This catches LLM hallucination at authoring time instead of letting auto-resolve hit the malformed contract at BUILD_GATE round 0.

**Carrier-block requirement for newly generated specs**: if any Requirement in the spec describes an observable runtime check (CLI command, test command, HTTP request, exit code, output substring, JSON shape), the `## Verification` ` ```json ` block **must** be present and contain at least one `verification_commands` entry that exercises that behavior. A new ideate-generated spec that has observable Requirements but omits the block silently degrades the auto-resolve gate to handwritten-spec backward-compat mode — that is the original real-user trap iter-0019.8 closes. The `--check` mode passes on absence (so pre-carrier handwritten specs being copied/refactored continue to validate), but a newly generated item-spec for a feature with runnable behavior must ship the block. Pure-design Requirements (e.g. "follow existing pattern X", "match the visual style of Y") may be the entire Requirements section — in that case the block is legitimately absent.

## Phase 5: BRIDGE

After DOCUMENT, print exactly one implementation handoff line per phase-1 item so the user can paste it into auto-resolve without rebuilding the spec path from memory:

```
Implementation:
/devlyn:auto-resolve "Implement per spec at docs/roadmap/phase-1/1.1-xxx.md"
/devlyn:auto-resolve "Implement per spec at docs/roadmap/phase-1/1.2-yyy.md"
```

Dependencies are already encoded in each spec's `Dependencies` section and in ROADMAP.md's status column — don't restate them here. The explicit `Implement per spec at <path>` wording is load-bearing: it's what tells auto-resolve to read the spec file and adopt its Requirements as done-criteria instead of generating fresh ones.

## Language

Generate all documents in the language the user communicates in. If the user mixes languages, match their primary language for prose and keep technical terms in English.
