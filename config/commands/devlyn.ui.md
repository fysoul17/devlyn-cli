---
name: design_styles
description: Generate 5 radically distinct UI style options from PRD
source: project
---

You are the **Lead Designer** with full creative authority. Create 5 portfolio-worthy HTML/CSS style samples that help stakeholders visualize design directions. These aren't mockups—they're design statements.

<context>
$ARGUMENTS
</context>

<input_handling>
The context above may contain:

- **PRD document**: Extract product goals, target users, and brand requirements
- **Product description**: Parse key features and emotional direction
- **Image references**: Analyze and replicate the visual style as closely as possible

If no input is provided, check for existing PRD at `docs/prd.md` or `README.md`.

### When Image References Are Provided

**Your primary goal shifts to replication, not invention.**

1. **Analyze the reference image(s) precisely:**

   - Extract exact color values (use color picker precision: #RRGGBB)
   - Identify font characteristics (serif/sans, weight, spacing, size ratios)
   - Map layout structure (grid, spacing rhythm, alignment patterns)
   - Note visual effects (shadows, gradients, blur, textures, border styles)
   - Capture motion cues (if animated reference or implied motion)

2. **Generate designs that match the reference:**

   - **Design 1-2**: Replicate the reference style as closely as possible, adapting to the PRD's content
   - **Design 3-5**: Variations that preserve the reference's core aesthetic while exploring different directions within that style

3. **Fidelity checklist for reference-based designs:**
   - [ ] Color palette within ±5% of reference values
   - [ ] Typography style matches (same category, similar weight/spacing)
   - [ ] Layout proportions preserved
   - [ ] Visual effects replicated (shadows, gradients, textures)
   - [ ] Overall "feel" is recognizably similar to reference

### When No Image References Are Provided

Follow the standard creative process: invent tension-based concept names, map across spectrums, and generate 5 radically different directions.
</input_handling>

<instructions>

## Phase 1: Extract Design DNA

Keep this brief—creative naming drives the design, not over-analysis.

```
**Product:** [one sentence]
**User:** [who, in what context, with what goal]
**Must convey:** [2-3 essential feelings]
```

## Phase 2: Invent 5 Creative Directions

### Check Existing Styles

Read `docs/design/` directory. If `style_N_*.html` files exist, continue numbering from N+1. New styles must be visually distinct from existing ones.

### Create 5 Concept Names

**Before any design work, invent 5 evocative names.**

Name format: `[word_A]_[word_B]` where:

- Word A and Word B create **tension or contrast**
- The combination should feel unexpected, not obvious
- Each word pulls the design in a different direction

Good patterns:

- [temperature]\_[movement]: warm vs cold, static vs dynamic
- [texture]\_[era]: rough vs smooth, retro vs futuristic
- [emotion]\_[structure]: soft vs rigid, chaotic vs ordered
- [material]\_[concept]: organic vs digital, heavy vs light

Avoid:

- Single adjectives
- Obvious pairings without tension
- Generic descriptors

**The name drives the design.** Tension in the name forces creative problem-solving.

### Map Each Concept Across 7 Spectrums

For each concept, mark its position. **Extremes create distinctiveness—avoid the middle.**

```
Concept: [name]

Layout:      Dense ●○○○○ Spacious
Color:       Monochrome ○○○○● Vibrant
Typography:  Serif ○○●○○ Display
Depth:       Flat ○○○○● Layered
Energy:      Calm ○●○○○ Dynamic
Theme:       Dark ●○○○○ Light
Shape:       Angular ○○○○● Curved
```

### Extreme Rule (Mandatory)

**Each design MUST have at least 2 extreme positions** (●○○○○ or ○○○○●).

Why: Middle positions (○○●○○) converge to "safe" averages. Extremes force distinctive choices.

### Verify Contrast

Before proceeding:

- [ ] Each design has **2+ extreme positions**
- [ ] No two concepts share the same position on 4+ spectrums
- [ ] Mix of dark and light themes across 5 designs
- [ ] Mix of angular and curved across 5 designs

## Phase 3: Define Concrete Specifications

For each concept, specify exact values—no adjectives.

```
### [Concept Name]

**Palette:**
- Background: #______
- Surface: #______
- Text: #______
- Text muted: #______
- Accent: #______

**Typography:**
- Font: [Google Font name]
- Headline: [size]px / [weight] / [letter-spacing]em
- Body: [size]px / [weight] / [line-height]

**Spacing:**
- Container max-width: [value]px
- Section padding: [value]px
- Element gap: [value]px
- Border-radius: [value]px

**Motion:**
- Duration: [value]s
- Easing: cubic-bezier([values])
- Stagger delay: [value]s
```

## Phase 4: Generate HTML Files

<use_parallel_tool_calls>
Write all 5 HTML files simultaneously by making 5 independent Write tool calls in a single response. These files have no dependencies on each other—do not write them sequentially. Maximize parallel execution for speed.
</use_parallel_tool_calls>

<frontend_aesthetics>
You tend to converge toward generic outputs. Avoid this:

**Typography:** Never use Inter, Roboto, Arial, Helvetica, Open Sans, Space Grotesk, or system fonts. Choose distinctive typefaces. Use weight extremes (100 vs 900, not 400 vs 600). Dramatic size jumps (3x+). Tight headline letter-spacing (-0.02em to -0.05em).

**Color:** One dominant + one sharp accent. Never pure #FFFFFF or #000000 backgrounds—add subtle tint. No purple gradients.

**Motion:** Focus on high-impact moments, not scattered micro-interactions.

- **Page load**: Orchestrated staggered reveals (vary `animation-delay` by 0.05-0.1s increments)
- **Scroll**: Use `IntersectionObserver` for scroll-triggered fade-ins (vanilla JS, no frameworks)
- **Hover**: Transform + opacity + subtle shadow shifts, not just color changes
- **Transitions**: Custom `cubic-bezier` easings that feel physical (e.g., `cubic-bezier(0.34, 1.56, 0.64, 1)` for bounce)
- **Advanced**: Gradient animations via `background-position`, `backdrop-filter` transitions, CSS `@property` for animatable custom properties
- **Restraint**: One dramatic sequence beats many small animations. If everything moves, nothing stands out.

**Backgrounds:** Never flat solid colors. Layer gradients, add subtle noise/grain, create atmosphere.

**Layout:** Break at least one standard pattern per design. Try asymmetry, overlap, bento grids, diagonal flow, or unexpected whitespace.
</frontend_aesthetics>

### File Requirements

| Requirement        | Details                                           |
| ------------------ | ------------------------------------------------- |
| **Path**           | `docs/design/style_{n}_{concept_name}.html`       |
| **Content**        | Realistic view matching product purpose           |
| **Self-contained** | Inline CSS, only Google Fonts external            |
| **Interactivity**  | Hover, active, focus states + page load animation |
| **Responsive**     | Basic mobile adaptation                           |
| **Real content**   | Actual copy from PRD, no lorem ipsum              |

### HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>[Product] - [Concept]</title>

    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=[Font]:[weights]&display=swap" rel="stylesheet" />

    <style>
      /* Concept: [name]
       Spectrum: L[x] C[x] T[x] D[x] E[x] Th[x] Sh[x]
       Extremes: [list which 2+ are extreme] */

      :root {
        --bg: #[hex];
        --surface: #[hex];
        --text: #[hex];
        --text-muted: #[hex];
        --accent: #[hex];
      }

      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }

      body {
        font-family: "[Font]", sans-serif;
        background: var(--bg);
        color: var(--text);
      }

      /* Page load: staggered reveal */
      .reveal {
        opacity: 0;
        transform: translateY(20px);
        animation: fadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      }
      .reveal:nth-child(1) {
        animation-delay: 0.1s;
      }
      .reveal:nth-child(2) {
        animation-delay: 0.15s;
      }
      .reveal:nth-child(3) {
        animation-delay: 0.2s;
      }

      @keyframes fadeUp {
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }

      /* Scroll-triggered: hidden until in view */
      .scroll-reveal {
        opacity: 0;
        transform: translateY(30px);
        transition: opacity 0.6s cubic-bezier(0.16, 1, 0.3, 1), transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
      }
      .scroll-reveal.visible {
        opacity: 1;
        transform: translateY(0);
      }

      /* Hover: physical-feeling bounce */
      .interactive {
        transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease;
      }
      .interactive:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 24px -8px rgba(0, 0, 0, 0.15);
      }
    </style>
  </head>
  <body>
    <!-- Semantic HTML with real content -->

    <script>
      // Scroll-triggered animations
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add("visible");
            }
          });
        },
        { threshold: 0.1 }
      );

      document.querySelectorAll(".scroll-reveal").forEach((el) => observer.observe(el));
    </script>
  </body>
</html>
```

## Phase 5: Verify Quality

### Per-Design Checklist

- [ ] Font is distinctive (not Inter/Roboto/Arial/system)
- [ ] Background has depth (not flat white/black)
- [ ] Page load animation with staggered delays
- [ ] Scroll-triggered reveals on below-fold content
- [ ] Hover states with transform + shadow (not just color)
- [ ] Custom easing (cubic-bezier), not default `ease` or `linear`
- [ ] CSS custom properties for colors
- [ ] Layout breaks at least one standard pattern

### Cross-Design Contrast

Each pair of designs must have 5+ obvious visual differences. If not, revise.

## Phase 6: Save & Report

Create `docs/design/` directory if needed. Save all 5 HTML files.

</instructions>

<output_format>

```
## Generated Styles

| # | Name | Spectrum (L/C/T/D/E/Th/Sh) | Extremes | Palette | Font |
|---|------|---------------------------|----------|---------|------|
| {n} | {name} | [x][x][x][x][x][x][x] | {which 2+} | #___, #___, #___ | {font} |

### Files
- docs/design/style_{n}_{name}.html
- ...

### Rationale
1. **{name}**: [1 sentence connecting to product requirements]
2. ...
```

</output_format>

Make bold choices. Each design should be portfolio-worthy—something you'd proudly present.
