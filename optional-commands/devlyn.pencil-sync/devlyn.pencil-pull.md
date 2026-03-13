# Pull Pencil Design into Code

Implement the selected Pencil design in code with exact visual fidelity. Work through one component at a time, verifying each against the design before moving on.

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
The coded implementation should be visually indistinguishable from the Pencil design. Small discrepancies — a few pixels of padding, a slightly different font weight, a missing border-radius — compound across components and produce a result that "looks off" even if no single difference is dramatic. Treat the Pencil design as the pixel-level specification and match it exactly.

The only areas where interpretation is needed:
- Interactive states (hover, focus, active) — Pencil can't represent these, so follow existing patterns in the codebase
- Responsive behavior — implement following existing responsive patterns
- Dynamic content — use the design's placeholder text for empty states
</goal>

## How to approach this

<setup>
Before writing any code, gather context:
1. Call `get_editor_state(include_schema: true)` to see the active .pen file and current selection. If the user has selected a frame, that's your target. If not, ask which frame/screen to implement.
2. Call `get_guidelines(topic: "code")` for Pencil's code generation rules. These supplement the project-specific conventions below.
3. Call `get_variables` to extract design tokens. Map each Pencil variable to its CSS custom property in `globals.css`. If new variables exist in Pencil that aren't in the CSS yet, add them to `globals.css` following the existing naming convention.

Design tokens flow: `Pencil variables → globals.css custom properties → Component CSS`. This chain keeps design and code in sync, so use CSS variables rather than hardcoding values.
</setup>

<implementation>
Work through components one at a time rather than attempting the full screen at once. This matters because verifying a single component is quick and reliable, while trying to verify an entire screen introduces too many variables — you can't tell which component introduced a discrepancy.

For each component:

**1. Read the design thoroughly**
Use `batch_get` with the component's node ID (`readDepth: 10`, `resolveVariables: true`) to get the complete tree. For components with SVGs, also set `includePathGeometry: true`. If it's a reusable component, read its instances too — they often override text, colors, or child visibility.

**2. Screenshot as ground truth**
Call `get_screenshot` on the component. Study the screenshot carefully — this is your specification. Note exact spacing, font sizes, colors, borders, shadows, border-radius, alignment, and text content.

**3. Check for existing code**
Search `src/components/` and `src/app/` for matching component names or CSS classes. If the component already exists, update it. Creating a duplicate leads to divergence over time.

**4. Implement**
Match every visual property from the design:
- Layout: flex direction, gap, padding, margin, alignment
- Sizing: exact width/height, `fill_container` → `width: 100%` or `flex: 1`, `fit_content` → `width: fit-content`
- Colors: map to CSS custom properties (`var(--bg-deep)`, `var(--accent)`, etc.)
- Typography: font-family, font-size, font-weight, line-height, letter-spacing, color
- Borders: width, color, radius (map to `var(--radius-*)`)
- Effects: box-shadow, opacity, backdrop-filter
- Text content: copy exactly, character for character
- Icons: match the icon, size, and color

When updating existing components, preserve all event handlers, state management, and data flow. Only change visual/layout properties.

**5. Verify**
Take another `get_screenshot` and compare. Check: are colors identical (not close)? Are font sizes and weights exact? Is spacing pixel-accurate? Are border-radius values correct? Is text character-for-character? Are all child elements present (count them)?

Fix any difference before moving to the next component.

**6. Report**
State what file was created/modified, list any new CSS variables added, and note any design decisions that required interpretation.
</implementation>

<integration_check>
After all components are implemented, verify the page-level layout:
- Use `batch_get` to read the complete target frame with full depth
- Check component ordering, spacing between components, and overall structure
- Use `snapshot_layout` to compare Pencil's computed layout rectangles against the CSS layout
</integration_check>

<examples>

**Example: Pulling a dashboard card component**

The Pencil design shows a card with `cornerRadius: 16` (maps to `var(--radius-md)`), `fill: $bg-deep`, `padding: 24`, and a title text in Space Grotesk at 14px/600. The `batch_get` output shows:
```
{type: "frame", cornerRadius: 16, fill: "$bg-deep", padding: 24, layout: "vertical", gap: 12,
 children: [{type: "text", content: "Active Projects", fontFamily: "Space Grotesk", fontSize: 14, fontWeight: 600}]}
```
Search code → find `.dash-card` in `dashboard.css`. Update it:
```css
.dash-card {
  background: var(--bg-deep);
  border-radius: var(--radius-md);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.dash-card h3 {
  font-family: var(--space);
  font-size: 14px;
  font-weight: 600;
}
```

**Example: Pulling a component with instance overrides**

A button component is reusable in Pencil. The base definition has `content: "Button"` and `fill: "$accent"`. But the instance in this frame overrides `content: "Deploy Now"` and adds a `descendants` override hiding an icon child. You need to:
1. Read both the base component and this specific instance
2. Implement the component with the overridden text "Deploy Now"
3. Respect the hidden icon — don't render it in this usage
4. Screenshot-verify the result matches the instance, not the base

</examples>

## Pencil MCP tools you'll use

| Task | Tool | Key Params |
|------|------|-----------|
| Check what's open | `get_editor_state` | `include_schema: true` |
| Read design nodes | `batch_get` | `readDepth`, `resolveVariables`, `includePathGeometry` |
| Take screenshot | `get_screenshot` | `nodeId` |
| Check layout | `snapshot_layout` | `maxDepth` |
| Get design tokens | `get_variables` | — |
| Get code guidelines | `get_guidelines` | `topic: "code"` |
