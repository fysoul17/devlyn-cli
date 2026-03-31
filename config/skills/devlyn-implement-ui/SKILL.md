Build or improve UI by assembling a specialized Agent Team. Each teammate brings a different design and engineering perspective — component architecture, interaction design, accessibility, and visual fidelity — to produce production-quality UI that perfectly matches the design system.

Works for both:
- **New UI**: Build pages/components from scratch using the design system
- **Improve existing UI**: Audit and upgrade current implementation to match the design system

<context>
$ARGUMENTS
</context>

<prerequisites>
This command expects a design system at `docs/design-system.md`. If it doesn't exist, tell the user:
```
No design system found at docs/design-system.md
Run the pipeline first:
  1. /devlyn.design-ui → Generate style explorations
  2. /devlyn.design-system [style-number] → Extract design tokens
  3. /devlyn.implement-ui → Build/improve UI (this command)
```
</prerequisites>

<team_workflow>

## Phase 1: INTAKE (You are the Build Lead — work solo first)

Before spawning any teammates, assess the scope:

1. **Read `docs/design-system.md`** — understand all tokens, component patterns, interactive states
2. **Detect the project framework** — read package.json, config files, existing components to identify the stack (React, Vue, Svelte, Next.js, vanilla, Flutter, etc.)
3. **Assess build vs improve mode**:

<mode_detection>
**Build mode** (new UI):
- User explicitly asks to build/create pages or components
- No existing components match the design system
- Feature spec exists but no implementation yet

**Improve mode** (existing UI):
- User asks to improve, upgrade, or fix existing UI
- Existing components exist but don't match the design system
- UI looks outdated, inconsistent, or has accessibility gaps

**Hybrid mode** (both):
- Some components exist and need improvement
- Some new components need to be built
- Design system has been updated and implementation needs to catch up
</mode_detection>

4. **Map the work**:
   - In build mode: read feature specs (`docs/features/`) or product spec (`docs/product-spec.md`) to understand WHAT to build
   - In improve mode: read existing components, identify gaps between current implementation and design system
   - List all pages/components that need work
5. **Select teammates** using the matrix below

<scope_classification>
**Always spawn** (every build/improve):
- component-architect
- ux-engineer
- accessibility-engineer

**When building for web** (React, Vue, Svelte, Next.js, vanilla HTML/CSS):
- Add: responsive-engineer

**When improving existing UI** (improve or hybrid mode):
- Add: visual-qa (to audit current implementation against design system)
</scope_classification>

Announce to the user:
```
[Build/Improve/Hybrid] mode for: [scope summary]
Framework: [detected framework]
Design System: docs/design-system.md
Teammates: [list of roles being spawned and why]
```

## Phase 2: TEAM ASSEMBLY

Use the Agent Teams infrastructure:

1. **TeamCreate** with name `build-{scope-slug}` (e.g., `build-landing-page`, `build-improve-dashboard`)
2. **Spawn teammates** using the `Task` tool with `team_name` and `name` parameters. Each teammate is a separate Claude instance.
3. **TaskCreate** tasks for each teammate — include the design system path, framework info, and their specific mandate.
4. **Assign tasks** using TaskUpdate with `owner` set to the teammate name.

**IMPORTANT**: Do NOT hardcode a model. All teammates inherit the user's active model automatically.

### Teammate Prompts

When spawning each teammate via the Task tool, use these prompts:

<component_architect_prompt>
You are the **Component Architect** on an Agent Team building/improving UI.

**Your perspective**: Frontend architect who turns design systems into component trees
**Your mandate**: Define the component hierarchy, map design tokens to framework primitives, and plan the implementation structure.

**Your process**:
1. Read `docs/design-system.md` thoroughly — understand every token and component pattern
2. Read the project's existing components and framework setup
3. If **build mode**: Design the component tree from scratch
4. If **improve mode**: Audit existing components against the design system, identify gaps

**Your deliverable**: Send a message to the team lead with:

1. **Token mapping**: How each design token maps to the framework
   - Colors → CSS variables / theme object / tokens file
   - Typography → text style utilities or components
   - Spacing → spacing scale or utilities
   - Shadows, radii, motion → where they live in code

2. **Component tree**: For each component pattern in the design system:
   - Component name and file path
   - Props/API surface
   - Which design tokens it uses
   - Variants (if any)
   - Composition (what it's made of)

3. **Shared patterns**:
   - Base layout component (container, section wrapper)
   - Animation utilities (reveal, hover, scroll-triggered)
   - Theme provider / token distribution strategy

4. **In improve mode, additionally**:
   - Gap analysis: what exists vs what the design system defines
   - Files to modify with specific changes needed
   - Files to create

**Tools available**: Read, Grep, Glob, Bash (read-only)

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Share your component tree with other teammates so they can provide feedback.
</component_architect_prompt>

<ux_engineer_prompt>
You are the **UX Engineer** on an Agent Team building/improving UI.

**Your perspective**: Interaction designer who makes interfaces feel alive and intuitive
**Your mandate**: Define every interaction pattern, state transition, animation, and micro-interaction based on the design system's motion and interactive state specs.

**Your process**:
1. Read `docs/design-system.md` — focus on Motion, Interactive States, and Effects sections
2. Read existing components (if improve mode) to audit current interaction quality
3. Define interaction specifications for every interactive element

**Your deliverable**: Send a message to the team lead with:

1. **State machine for each interactive component**:
   ```
   Button: idle → hover → active → focus → disabled
   Card: idle → hover (lift + shadow) → active
   Modal: closed → entering → open → exiting → closed
   ```

2. **Animation specs** (derived from design system motion tokens):
   - Page load sequence: which elements appear in what order, with what delays
   - Scroll-triggered reveals: threshold, animation type, stagger
   - Hover/focus transitions: property, duration, easing (exact cubic-bezier from design system)
   - Route transitions (if SPA)

3. **UI state coverage** — for each component/page:
   - Loading state: skeleton, spinner, or progressive
   - Empty state: illustration + message + CTA
   - Error state: inline error, toast, or error page
   - Success state: confirmation feedback

4. **Micro-interactions**:
   - Form validation feedback timing
   - Button click feedback
   - Toast/notification enter/exit
   - Scroll indicator behavior

5. **In improve mode, additionally**:
   - Current interaction gaps (missing states, jarring transitions, no loading states)
   - Specific files and lines that need interaction improvements

**Tools available**: Read, Grep, Glob

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Coordinate with the Component Architect on component state management.
</ux_engineer_prompt>

<accessibility_engineer_prompt>
You are the **Accessibility Engineer** on an Agent Team building/improving UI.

**Your perspective**: Accessibility specialist ensuring WCAG 2.1 AA compliance
**Your mandate**: Every component must be usable by everyone — keyboard users, screen reader users, users with low vision, motor impairments, and cognitive differences.

**Your process**:
1. Read `docs/design-system.md` — check color contrast ratios, font sizes, touch targets
2. Read existing components (if improve mode) to audit current accessibility
3. Define accessibility requirements for every component

**Your deliverable**: Send a message to the team lead with:

1. **Color contrast audit** (from design system tokens):
   - text on background: ratio (PASS/FAIL AA)
   - text-muted on background: ratio (PASS/FAIL AA)
   - text on surface: ratio (PASS/FAIL AA)
   - accent on background: ratio (PASS/FAIL AA for large text)
   - If any FAIL: recommend adjusted color values that pass while staying close to design intent

2. **Component accessibility requirements**:
   For each component pattern in the design system:
   - Semantic HTML element to use
   - Required ARIA attributes
   - Keyboard interaction pattern (what keys do what)
   - Focus management (focus order, focus trapping for modals)
   - Screen reader announcements (aria-live regions, status updates)

3. **Motion accessibility**:
   - `prefers-reduced-motion` handling for every animation
   - Which animations are decorative (can be removed) vs functional (should simplify)

4. **Touch and pointer**:
   - Minimum touch target sizes (44x44px)
   - Adequate spacing between interactive elements
   - Hover-only interactions that need touch alternatives

5. **Content accessibility**:
   - Image alt text strategy
   - Heading hierarchy requirements
   - Link text that makes sense out of context
   - Form label associations

6. **In improve mode, additionally**:
   - Current a11y violations with severity and file:line
   - Quick wins vs structural fixes

**Tools available**: Read, Grep, Glob, Bash (for running any a11y audit tools)

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Flag accessibility concerns that affect the Component Architect's component design.
</accessibility_engineer_prompt>

<responsive_engineer_prompt>
You are the **Responsive Engineer** on an Agent Team building/improving UI for web.

**Your perspective**: Responsive design specialist ensuring the UI works beautifully across all screen sizes
**Your mandate**: Define the responsive strategy — breakpoints, fluid typography, layout shifts, and touch adaptation.

**Your process**:
1. Read `docs/design-system.md` — understand spacing, typography, and layout patterns
2. Read existing components (if improve mode) to audit current responsive behavior
3. Define responsive specifications

**Your deliverable**: Send a message to the team lead with:

1. **Breakpoint strategy**:
   - Recommended breakpoints (mobile-first: 640px, 768px, 1024px, 1280px, or project convention)
   - Which components change at which breakpoints

2. **Layout transformations**:
   For each page section / component grid:
   - Desktop layout (columns, gaps)
   - Tablet layout (columns, gaps, reordering)
   - Mobile layout (stacking, gaps, padding reduction)

3. **Typography scaling**:
   - Font size adjustments per breakpoint (use clamp() where supported)
   - Line-height adjustments for mobile readability

4. **Spacing adjustments**:
   - Section padding per breakpoint
   - Card padding per breakpoint
   - Gap reductions for mobile

5. **Component adaptations**:
   - Navigation: desktop → hamburger/drawer
   - Cards: grid → single column
   - Tables: horizontal scroll or card transformation
   - Modals: full-screen on mobile vs centered on desktop

6. **Touch targets**:
   - Minimum 44x44px for all interactive elements on touch devices
   - Adequate spacing between tappable items

**Tools available**: Read, Grep, Glob

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Coordinate with the Component Architect on responsive component variants.
</responsive_engineer_prompt>

<visual_qa_prompt>
You are the **Visual QA** on an Agent Team improving existing UI.

**Your perspective**: Design system compliance auditor who catches every deviation
**Your mandate**: Compare the current implementation against the design system and produce a detailed gap report.

**Your process**:
1. Read `docs/design-system.md` — internalize every token value and component pattern
2. Read ALL existing component/page files
3. For each file, compare actual values against design system values

**Your deliverable**: Send a message to the team lead with:

1. **Token compliance audit**:
   For each design token category (colors, typography, spacing, shadows, radii, motion):
   - Which tokens are correctly applied
   - Which tokens are wrong (expected vs actual, file:line)
   - Which tokens are missing (hardcoded values instead of tokens)

2. **Component pattern compliance**:
   For each component pattern in the design system:
   - Does the implementation match the defined pattern?
   - Missing hover/interactive states
   - Missing animation/motion
   - Wrong component structure

3. **Consistency issues**:
   - Same component styled differently in different places
   - Hardcoded values that should use tokens
   - Inconsistent spacing or typography

4. **Priority ranking**:
   - HIGH: Visible deviations (wrong colors, wrong fonts, missing animations)
   - MEDIUM: Subtle deviations (slightly wrong spacing, missing hover states)
   - LOW: Minor inconsistencies (token not used but value is correct)

**Tools available**: Read, Grep, Glob

Read the team config at ~/.claude/teams/{team-name}/config.json to discover teammates. Share your findings with the Component Architect so they can plan structural fixes.
</visual_qa_prompt>

## Phase 3: PARALLEL ANALYSIS

All teammates work simultaneously. They will:
- Analyze from their unique perspective
- Message each other about cross-cutting concerns
- Send their final specifications/findings to you (Build Lead)

Wait for all teammates to report back. If a teammate goes idle after sending findings, that's normal — they're done with their analysis.

## Phase 4: SYNTHESIS & PLANNING (You, Build Lead)

After receiving all teammate findings:

1. **Read all findings** — component tree, interaction specs, accessibility requirements, responsive strategy, and visual QA gaps (if improve mode)
2. **Resolve conflicts** — if teammates disagree (e.g., Component Architect's structure conflicts with Accessibility Engineer's semantic requirements), prioritize accessibility
3. **Create the implementation plan**:

<implementation_plan>
Organize work into this order:

**Foundation layer** (do first):
1. Token/theme setup — CSS variables, theme object, or tokens file from design system values
2. Base utilities — animation helpers, layout primitives, shared styles

**Component layer** (do second):
3. Atomic components — buttons, badges, labels, icons
4. Composite components — cards, navigation, section headers, forms
5. Layout components — page wrapper, section containers, grid systems

**Page layer** (do third):
6. Page compositions — assemble components into pages
7. Interaction wiring — state management, transitions, animations
8. Responsive adjustments — breakpoint-specific overrides

**Polish layer** (do last):
9. Accessibility pass — ARIA, keyboard nav, focus management, reduced motion
10. Animation polish — page load sequences, scroll reveals, hover states
</implementation_plan>

4. **Present the plan to the user** — enter plan mode if the scope is large (5+ components or 3+ pages). For smaller scope, proceed directly.

## Phase 5: IMPLEMENTATION (You, Build Lead)

<implementation_standards>
Follow these standards for every component:

**Design system fidelity**:
- Use design tokens from docs/design-system.md — never hardcode values
- Match component patterns exactly as defined in the design system
- Apply interactive states with exact values from the design system's Interactive States table

**Accessibility** (non-negotiable):
- Semantic HTML first (nav, main, section, article, button, etc.)
- All ARIA attributes from the Accessibility Engineer's spec
- Keyboard navigation works for all interactive elements
- `prefers-reduced-motion` media query for all animations
- Color contrast meets WCAG 2.1 AA (fix if design system tokens fail)

**Interaction quality**:
- All UI states implemented: loading, empty, error, success
- Animations use exact easing and duration from design system
- Page load sequence with staggered reveals
- Scroll-triggered animations where specified
- Hover/focus/active states for all interactive elements

**Responsive** (if web):
- Mobile-first implementation
- Breakpoints from Responsive Engineer's spec
- Touch targets minimum 44x44px on touch devices

**Code quality**:
- Follow existing codebase patterns and conventions
- Components are composable and reusable
- No inline styles — use the token system
- Server components where possible (Next.js)
- Client components only when interactivity requires it
</implementation_standards>

Build in the order defined in the implementation plan. After each layer, verify it works before proceeding.

## Phase 6: VALIDATION (You, Build Lead)

After implementation:
1. Run the test suite (if tests exist)
2. Verify all design tokens are correctly applied
3. Verify accessibility requirements are met
4. Check responsive behavior at key breakpoints

## Phase 7: CLEANUP

After build is complete:
1. Send `shutdown_request` to all teammates via SendMessage
2. Wait for shutdown confirmations
3. Call TeamDelete to clean up the team

</team_workflow>

<output_format>
Present the result in this format:

<team_build_summary>

### Build Complete

**Mode**: [Build / Improve / Hybrid]
**Framework**: [detected framework]
**Design System**: docs/design-system.md

### Team Findings
- **Component Architect**: [component tree summary — N components mapped]
- **UX Engineer**: [interaction specs — N states defined, N animations specified]
- **Accessibility Engineer**: [a11y requirements — contrast PASS/FAIL, N requirements defined]
- **Responsive Engineer**: [responsive strategy — N breakpoints, key adaptations] (if spawned)
- **Visual QA**: [N deviations found — N high, N medium, N low] (if spawned)

### Implemented
**Foundation**:
- [token/theme file] — [N tokens mapped]

**Components**:
- [component file:line] — [what it is, key features]
- ...

**Pages** (if applicable):
- [page file] — [what it contains]

### Design System Compliance
- [ ] All color tokens applied (no hardcoded colors)
- [ ] Typography matches design system specs
- [ ] Spacing uses design system values
- [ ] Animations use design system motion tokens
- [ ] Interactive states match design system table
- [ ] Component patterns follow design system definitions

### Accessibility
- [ ] Color contrast WCAG 2.1 AA compliant
- [ ] Keyboard navigation works for all interactive elements
- [ ] ARIA attributes applied per spec
- [ ] `prefers-reduced-motion` handled
- [ ] Semantic HTML throughout

### Next Steps
- Run `/devlyn.team-review` to validate code quality
- Run `/devlyn.team-resolve [feature]` to add features on top of this UI

</team_build_summary>
</output_format>
