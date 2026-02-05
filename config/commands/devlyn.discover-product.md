Scan the codebase to generate a feature-oriented product document.

<procedure>
1. Read project metadata files in parallel: package.json, README.md, CLAUDE.md, any config files
2. Scan directory structure to understand architecture: `ls -la` on root, src/, app/, components/, pages/, api/
3. Identify features by analyzing:
   - Route definitions (pages, API endpoints)
   - Major components and their purposes
   - State management (stores, contexts)
   - External integrations (APIs, services, databases)
4. For each feature, trace through the code to understand its scope
5. Generate the feature document using the output format below
</procedure>

<investigate_thoroughly>
Read actual code files, not just file names. Understand what each feature DOES by examining implementations. Do not guess features from names alone. Use parallel tool calls when reading multiple files.
</investigate_thoroughly>

<feature_identification>

## Where to Look for Features

- `/app` or `/pages` → User-facing routes and pages
- `/components` → UI features and reusable functionality
- `/api` or `/server` → Backend capabilities
- `/hooks` or `/lib` → Core functionality and utilities
- `/store` or `/context` → State-managed features
- Config files → Integrations and external services

## What Qualifies as a Feature

A feature is user-facing functionality or a distinct capability:

- ✓ "Real-time transcription" → feature
- ✓ "User authentication" → feature
- ✓ "Export to PDF" → feature
- ✗ "Button component" → implementation detail
- ✗ "API wrapper" → implementation detail

## Feature Attributes to Capture

For each feature identify:

- Name — clear, user-oriented label
- Description — what it does in 1-2 sentences
- Status — [Implemented / Partial / Planned] based on code evidence
- Key files — main files that implement this feature
- Dependencies — external services, APIs, or libraries required

</feature_identification>

<output_format>
Generate a markdown document structured as follows:

```markdown
# [Project Name] — Feature Documentation

> Auto-generated from codebase scan on [date]

## Overview

[2-3 sentences: what this product is and its primary purpose]

## Tech Stack

- **Framework**: [e.g., Next.js 15, React 19]
- **Language**: [e.g., TypeScript 5.x]
- **Database**: [e.g., Supabase, PostgreSQL]
- **Key Libraries**: [list major dependencies]

---

## Features

### 1. [Feature Name]

**Status**: Implemented | Partial | Planned

[1-2 sentence description of what this feature does for the user]

**Key Files**:

- `src/components/FeatureComponent.tsx` — main UI
- `src/hooks/useFeature.ts` — logic
- `src/api/feature.ts` — backend

**Dependencies**: [External services, APIs]

---

### 2. [Feature Name]

...

---

## Architecture Notes

[Brief description of how features connect: data flow, state management patterns, API structure]

## Integrations

| Service          | Purpose                 | Config Location    |
| ---------------- | ----------------------- | ------------------ |
| [e.g., Supabase] | [e.g., Auth + Database] | [e.g., .env.local] |

## Not Yet Implemented

[Features found in comments, TODOs, or partial code that aren't complete]
```

</output_format>

<task>
Scan this codebase now. Generate the feature document and output it in a code block. Be thorough — read actual implementations to understand features, not just file names.
</task>
