# Push Codebase Design to Pencil

Read the current UI implementation and recreate it as a matching design in Pencil, so the .pen canvas accurately reflects what's live in code.

<project_context>
- Next.js 16 + React 19, Server Components by default
- Custom CSS with CSS variables (no Tailwind) — tokens live in `src/app/globals.css`
- Three visual zones, each with its own CSS file and class prefix:
  - Marketing (`marketing.css`) — cinematic, descriptive class names
  - Auth (`auth.css`) — minimal, `auth-` prefix
  - Dashboard (`dashboard.css`) — functional, `dash-` prefix
- Design system reference: `docs/design-system.md`
</project_context>

<goal>
The Pencil file should be a faithful mirror of the coded UI. When someone opens the .pen file, they should see exactly what the live site looks like — same colors, spacing, typography, radii, and component structure. This matters because the .pen file becomes the source of truth for future design iterations: if it drifts from code, every subsequent design change will introduce unintended differences.
</goal>

## How to approach this

<setup>
Start by understanding the current state:
1. Call `get_editor_state(include_schema: true)` to see if a .pen file is already open. If not, either create one with `open_document("new")` or ask which .pen file to target.
2. Read the codebase's design tokens from `src/app/globals.css` and `docs/design-system.md`. Also read the zone-specific CSS file for whichever zone the user wants to push.
3. Sync tokens into Pencil: use `get_variables` to check what exists, then `set_variables` to create/update variables matching the CSS custom properties (colors, radii, fonts). Use Pencil variables throughout — this keeps themes connected between code and Pencil.
</setup>

<implementation>
Work through each component or section one at a time rather than trying to build the entire page in one pass. Building incrementally lets you verify each piece against the code before moving on, which prevents small errors from compounding into large drift.

For each component:
1. Read the `.tsx` file and its CSS to understand layout, children, and styles
2. Build the matching frame structure in Pencil using `batch_design` (max 25 operations per call)
3. Apply styles using Pencil variables — match exact pixel values from CSS for spacing, font sizes, border-radius, etc.
4. Take a `get_screenshot` and compare against the coded version
5. Fix any discrepancies before moving on

Name Pencil frames and nodes to match CSS class names or React component names. This makes it easy to trace between code and design later.
</implementation>

<examples>

**Example: Pushing a dashboard sidebar**

The sidebar component lives at `src/components/dashboard/Sidebar.tsx` with styles in `dashboard.css` using `.dash-sidebar`. You would:
1. Read both files to extract: width (280px via `--sidebar-width`), background color (`var(--bg-deep)`), flex layout (vertical, gap), and all child nav items
2. Create a frame in Pencil with `width: 280`, `fill: $bg-deep`, `layout: vertical`, matching gap/padding
3. Add child text nodes and icon frames matching each nav link
4. Screenshot and verify dimensions, colors, and text content match

**Example: Pushing a glass panel component**

The `.glass-panel` class in `globals.css` has `border-radius: var(--radius-3xl)` (44px), `backdrop-filter: blur(20px)`, and a liquid highlight. You would:
1. Create a frame with `cornerRadius: 44`, matching the backdrop-filter effect as closely as Pencil supports
2. Use the `$glass-bg` variable for background
3. Verify the panel looks visually consistent with the coded version

</examples>

## Pencil MCP tools you'll use

| Task | Tool | Key Params |
|------|------|-----------|
| Check what's open | `get_editor_state` | `include_schema: true` |
| Open/create .pen file | `open_document` | `"new"` or file path |
| Read design nodes | `batch_get` | `readDepth`, `searchDepth` |
| Take screenshot | `get_screenshot` | `nodeId` |
| Check layout | `snapshot_layout` | `maxDepth` |
| Get/set design tokens | `get_variables` / `set_variables` | — |
| Build design | `batch_design` | operations string (max 25 ops) |
