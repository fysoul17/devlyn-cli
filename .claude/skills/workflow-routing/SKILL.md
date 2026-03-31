# Workflow Routing

Guide for choosing the right devlyn command at each stage of development. This skill helps you pick the optimal workflow instead of defaulting to a general approach.

## Trigger

- User describes a task without specifying a command
- User asks "how should I approach this?" or "what command should I use?"
- Beginning of a new feature, bug fix, or maintenance task
- Context suggests a specific workflow would be more effective than a generic approach

## SDLC Phase Map

Match the user's current activity to the right command:

### Discovery & Planning
| Situation | Command | Why |
|-----------|---------|-----|
| Need to understand what the project does | `/devlyn.discover-product` | Generates feature-oriented product documentation from code |
| Need to define a new product | `/devlyn.product-spec` | Creates or updates product spec documents |
| Need to plan a specific feature | `/devlyn.feature-spec` | Transforms product specs into implementable feature specs |
| Need to decide what to build next | `/devlyn.recommend-features` | Prioritizes top 5 features by value and readiness |

### Design
| Situation | Command | Why |
|-----------|---------|-----|
| Need UI style exploration (solo) | `/devlyn.design-ui` | Generates 5 distinct style options |
| Need team-based design exploration | `/devlyn.team-design-ui` | 5-person design team with diverse perspectives |
| Need to extract design tokens | `/devlyn.design-system` | Converts chosen style into reusable token system |
| Need to build or improve UI | `/devlyn.implement-ui` | Team-based UI implementation from design system |

### Implementation & Debugging
| Situation | Command | Why |
|-----------|---------|-----|
| Simple bug (single module, clear cause) | `/devlyn.resolve` | Solo root cause analysis with 5 Whys |
| Complex bug (multi-module, unclear cause) | `/devlyn.team-resolve` | Multi-perspective investigation team |
| Feature implementation on existing UI | `/devlyn.team-resolve [feature]` | Team approach for feature work |

### Review & Quality
| Situation | Command | Why |
|-----------|---------|-----|
| Quick review (few files) | `/devlyn.review` | Solo review with severity framework |
| Thorough review (many files, security-sensitive) | `/devlyn.team-review` | Multi-reviewer team coverage |

### Maintenance
| Situation | Command | Why |
|-----------|---------|-----|
| Remove dead code and tech debt | `/devlyn.clean` | 5-category codebase health analysis |
| Targeted cleanup (deps, tests, etc.) | `/devlyn.clean [category]` | Focused sweep on one area |
| Sync documentation with codebase | `/devlyn.update-docs` | Cleans stale content, preserves roadmaps |
| Targeted doc update | `/devlyn.update-docs [area]` | Focused update on specific doc area |

## Escalation Paths

When a solo command isn't enough:

- `/devlyn.resolve` → escalate to `/devlyn.team-resolve` if issue spans 3+ modules or root cause is unclear
- `/devlyn.review` → escalate to `/devlyn.team-review` if changeset is 10+ files or touches multiple domains
- `/devlyn.design-ui` → escalate to `/devlyn.team-design-ui` if design needs multi-perspective exploration

## Common Workflow Sequences

**New feature from scratch:**
`product-spec` → `feature-spec` → `design-ui` → `design-system` → `implement-ui` → `review`

**Bug fix:**
`resolve` (or `team-resolve`) → `review` (or `team-review`)

**Periodic maintenance:**
`clean` → `update-docs` → `review`

**Post-launch refinement:**
`discover-product` → `recommend-features` → `feature-spec` → implement → `review`
