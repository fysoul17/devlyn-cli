---
description: Extract all design values from selected style for exact reproduction
argument-hint: <style-number> [platform] (e.g., "3", "3 flutter", "style 2 web")
allowed-tools: Bash(ls:*), Bash(cat:*), Bash(grep:*), View, Edit, Write
---

Extract design values from a style preview HTML to generate a framework-agnostic design reference.

<context>
User input: $ARGUMENTS
Available styles: !`ls -1 docs/design/style_*.html 2>/dev/null || echo "No styles found"`
</context>

<input_parsing>

Parse two values from input:

1. **Style number** (required): "3", "style 3", or "style_3_concept_name" all resolve to style 3

2. **Platform** (optional, defaults to "web"):
   - `web` — HTML/CSS, React, Vue, Svelte, Next.js
   - `flutter` — Dart/Flutter
   - `native` — iOS (SwiftUI) / Android (Compose)
   - `desktop` — Electron, Tauri, PyQt
   - `terminal` — CLI apps with color support

</input_parsing>

<goal>

Create a design reference document that enables any AI agent to:

1. Apply correct visual styling (colors, typography, spacing, shadows, motion)
2. Build components that match the design language (patterns, behaviors, icon approach)

This document contains **values and patterns**—no framework-specific implementation code. The implementing agent determines the correct syntax based on the actual project setup.

**Important distinction**:

- This document defines HOW things should look (reusable across any page structure)
- Feature specs define WHAT to build (page structure, sections, content)
- An agent uses both: feature spec for structure + this document for styling

</goal>

<extraction_requirements>

Extract all concrete values that define the design's appearance and reusable component patterns.

<colors>
Extract every color used:
- Background, surface, text primary, text secondary
- Accent colors (primary, secondary if present)
- Borders, dividers, hover states
- Any gradients (with exact color stops and direction)

Format: hex values (e.g., #F4F7FA)
</colors>

<typography>
Extract the exact font configuration:
- Font family name (exact Google Fonts spelling)
- All font weights used (e.g., 300, 400, 600, 700)

For each text level (H1, H2, H3, Body, Body Large, Small/Caption, Label):

- Size in pixels
- Weight
- Letter-spacing (em or px)
- Line-height (unitless ratio)
  </typography>

<spacing>
Extract actual pixel values used, not abstract scales:
- Section/page padding
- Hero section padding (if different)
- Component/card padding (large and small variants)
- Element gap (between buttons, cards)
- Tight gap (icon + text, inline elements)
- Navigation gaps
- Section header margin-bottom
</spacing>

<shape>
Extract border-radius values:
- Cards and containers
- Feature icons
- Small icons
- Buttons and pills (often "full" or 100px)
- CTA sections (if different)
</shape>

<shadows>
Extract complete box-shadow CSS values:
- Default/subtle shadow
- Navigation/badge shadow
- Floating card shadow
- Hover state shadow
- Button hover shadow

Include the full value: offset, blur, spread, color with alpha.
</shadows>

<motion>
Extract animation timing:
- Easing function (exact cubic-bezier or keyword)
- Base transition duration
- Enter/appear animation duration
- Scroll-triggered transition duration
- Stagger delay between items
- Any cyclic animation durations (float, drift effects)
</motion>

<effects>
Only if present in the design:
- Background effects (orbs, gradients, patterns)
- Glassmorphism (backdrop-filter blur value, background opacity)
- Gradient text treatment
- Any texture overlays
</effects>

<components>
Extract reusable component patterns found in the design. For each distinct component type:

1. **Navigation** (if present):

   - Layout type (fixed, sticky, static)
   - Visual treatment (solid, glassmorphism, transparent)
   - Elements included (logo style, link style, CTA style)

2. **Cards** (identify all card variants):

   - Name/purpose (feature card, stat card, testimonial card, etc.)
   - Icon approach: emoji, SVG, or icon font
   - If emoji: note this explicitly
   - Icon container style (size, background, radius)
   - Content structure (what elements: icon, title, description, stat, etc.)
   - Hover behavior (transform, shadow change, with duration)

3. **Buttons** (identify all variants):

   - Primary, secondary, ghost styles
   - Hover transforms and shadow changes

4. **Badges/Labels**:

   - Visual style (pill, tag, etc.)
   - Any animated elements (pulse dots, etc.)

5. **Section Headers**:

   - Label + title + description pattern
   - Alignment (centered, left)

6. **Special Elements**:
   - Any unique patterns (floating cards, step indicators, etc.)
   - Animation behaviors

For each component, describe it as a reusable pattern that can be applied regardless of how many times it appears or what content it contains.
</components>

<interactive_states>
Document hover/active/focus states for interactive elements:

- What property changes (transform, shadow, background, scale, opacity)
- From value → To value
- Duration and easing

Format as a reference table.
</interactive_states>

<character>
Summarize the design's personality:
- Theme: Light or Dark
- Shape language: Angular, Curved, or Mixed
- Density: Spacious or Dense
- Energy: Calm, Dynamic, or Playful
</character>

</extraction_requirements>

<output_format>

Generate `docs/design-system.md` with this structure:

```markdown
# Design Style: {Concept Name}

> {One sentence capturing the design's mood and intent}

**Platform**: {platform}
**Source**: `{source filename}`

---

## Implementation Note

This document defines the visual design language—HOW things should look.

When implementing:

1. Use your **feature spec** for page structure (WHAT sections/components to build)
2. Use **this document** for styling those components (HOW they should look)
3. Apply values using syntax appropriate for your framework

---

## Colors

| Role                  | Value     |
| --------------------- | --------- |
| Background            | `#______` |
| Surface               | `#______` |
| Text                  | `#______` |
| Text Muted            | `#______` |
| Accent                | `#______` |
| {additional roles...} | `#______` |

**Gradients** (if present):

- {Name}: `{direction}deg, {color1} {stop1}%, {color2} {stop2}%`

## Typography

**Font Family**: {exact name} (with {fallback} for {language} if applicable)
**Weights**: {comma-separated list}

| Element       | Size  | Weight | Letter-spacing | Line-height |
| ------------- | ----- | ------ | -------------- | ----------- |
| H1            | {n}px | {n}    | {n}em          | {n}         |
| H2            | {n}px | {n}    | {n}em          | {n}         |
| H3            | {n}px | {n}    | {n}em          | {n}         |
| Body          | {n}px | {n}    | —              | {n}         |
| Body Large    | {n}px | {n}    | —              | {n}         |
| Small/Caption | {n}px | {n}    | —              | {n}         |
| Label         | {n}px | {n}    | —              | {n}         |

## Spacing

| Context                      | Value                            |
| ---------------------------- | -------------------------------- |
| Section padding              | {n}px vertical, {n}px horizontal |
| Hero padding                 | {top}px top, {bottom}px bottom   |
| Card padding (large)         | {n}px                            |
| Card padding (small)         | {n}px                            |
| Element gap                  | {n}px                            |
| Tight gap                    | {n}px                            |
| Section header margin-bottom | {n}px                            |

## Shape

| Context          | Radius       |
| ---------------- | ------------ |
| Cards/Containers | {n}px        |
| Icons (large)    | {n}px        |
| Icons (small)    | {n}px        |
| Buttons/Pills    | {n}px (full) |

## Shadows

| Name         | Value                 |
| ------------ | --------------------- |
| Subtle       | `{full shadow value}` |
| Card         | `{full shadow value}` |
| Card Hover   | `{full shadow value}` |
| Float        | `{full shadow value}` |
| Button Hover | `{full shadow value}` |

## Motion

| Property            | Value                              |
| ------------------- | ---------------------------------- |
| Easing (soft)       | `cubic-bezier({a}, {b}, {c}, {d})` |
| Easing (bounce)     | `cubic-bezier({a}, {b}, {c}, {d})` |
| Base duration       | {n}s                               |
| Hover duration      | {n}s                               |
| Enter duration      | {n}s                               |
| Stagger             | {n}s                               |
| {Cyclic animations} | {n}s                               |

## Effects

{Only include sections that exist in the source design}

**Background Elements** (if present):

- {Description with sizes, colors, blur, positions, animations}

**Glassmorphism** (if present):

- Background: `rgba({r}, {g}, {b}, {a})`
- Backdrop blur: {n}px

**Gradient Text** (if present):

- Applied to: {list elements}
- CSS: background-clip text with transparent fill

---

## Component Patterns

Reusable patterns that define how components should look, regardless of page structure.

### Icon Approach

- **Type**: {emoji | SVG | icon font}
- **Container**: {size}px, {background}, {radius}px radius
  {If emoji, note: "Use emoji characters directly, not icon libraries"}

### Navigation

- **Position**: {fixed center | sticky top | etc.}
- **Style**: {glassmorphism | solid | transparent}
- **Elements**: Logo ({style}), Links ({style}), CTA button ({style})

### Card: Feature

- **Use for**: Feature highlights, service descriptions
- **Structure**: Icon container → Title → Description
- **Icon**: {size}px container, {background style}
- **Hover**: {transform}, {shadow change}, {duration}

### Card: Stat

- **Use for**: Metrics, numbers, KPIs
- **Structure**: Large value (gradient text) → Label
- **Hover**: {transform}, {duration}

### Card: {Other variants found...}

{Document each distinct card pattern}

### Button: Primary

- **Style**: {gradient/solid} background, {text color}
- **Hover**: {transform}, {shadow}

### Button: Secondary

- **Style**: {background}, {border if any}
- **Hover**: {changes}

### Badge/Label

- **Style**: Pill shape, {background}, {text style}
- **Animation**: {if any, e.g., pulse dot}

### Section Header

- **Pattern**: Label badge (optional) → H2 title → Description (optional)
- **Alignment**: {centered | left}
- **Spacing**: {margin-bottom}px below

### {Special Patterns}

{Document any unique patterns like floating cards, step indicators, etc.}

---

## Interactive States

| Component                                  | Trigger | Property  | From   | To               | Duration |
| ------------------------------------------ | ------- | --------- | ------ | ---------------- | -------- |
| Feature Card                               | hover   | transform | none   | translateY(-8px) | {n}s     |
| Feature Card                               | hover   | shadow    | subtle | card-hover       | {n}s     |
| Button Primary                             | hover   | transform | none   | translateY(-3px) | {n}s     |
| Button Primary                             | hover   | shadow    | none   | button-hover     | {n}s     |
| {continue for all interactive elements...} |         |           |        |                  |          |

---

## Character

- **Theme**: {Light | Dark}
- **Shape**: {Angular | Curved | Mixed}
- **Density**: {Spacious | Dense}
- **Energy**: {Calm | Dynamic | Playful}

---

## Token Reference

Quick reference for implementation.

### Colors
```

color-bg: #**\_\_**
color-surface: #**\_\_**
color-text: #**\_\_**
color-text-muted: #**\_\_**
color-accent: #**\_\_**
gradient-primary: {direction}, {stops}

```

### Typography
```

font-family: {name}, {fallback}
font-weight-regular: {n}
font-weight-semibold: {n}
font-weight-bold: {n}

```

### Spacing
```

space-section: {n}px
space-component: {n}px
space-element: {n}px
space-tight: {n}px

```

### Shape
```

radius-card: {n}px
radius-icon: {n}px
radius-button: full

```

### Motion
```

ease-soft: cubic-bezier({values})
ease-bounce: cubic-bezier({values})
duration-base: {n}s
duration-hover: {n}s

```

---

_Generated from: `{source filename}`_
```

</output_format>

<platform_adaptations>

Adjust the Token Reference section based on platform:

**flutter**: Include Dart-style comments showing Color() and Duration() syntax as reference
**native**: Note that colors should be added to asset catalogs
**terminal**: Include ANSI color code mappings

Keep these as **reference comments**, not copy-paste code.

</platform_adaptations>

<quality_verification>

Before saving, verify completeness:

**Values extraction**:

- [ ] All colors extracted with valid hex values
- [ ] Font name matches exact Google Fonts spelling
- [ ] Typography table complete for all text levels
- [ ] Spacing values are concrete pixels
- [ ] Border radius values for all contexts
- [ ] Shadow values are complete CSS
- [ ] Easing is exact cubic-bezier
- [ ] Animation durations in seconds

**Component patterns**:

- [ ] Icon approach clearly stated (emoji vs SVG vs font)
- [ ] All card variants documented with hover behavior
- [ ] Button variants documented
- [ ] Navigation pattern documented
- [ ] Section header pattern documented
- [ ] Special/unique patterns documented

**Interactive states**:

- [ ] All hover transforms documented
- [ ] All shadow transitions documented
- [ ] Durations specified for each

**Reproduction test**: Could another agent read this document and build components that look identical, regardless of what page structure they're implementing?

</quality_verification>

<execution>

1. Parse style number and platform from $ARGUMENTS
2. Read the matching `docs/design/style_{n}_*.html` file
3. Extract all values following the extraction requirements
4. Extract all component patterns
5. Document all interactive states
6. Generate `docs/design-system.md` following the output format
7. Confirm what was created and note the source file

If the style file doesn't exist, list the available options.

</execution>
