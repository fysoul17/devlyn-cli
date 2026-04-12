# Asset Creator — Style Guide

This document defines the art direction defaults and per-category templates. In production, the meta prompt (extracted from a reference asset) overrides the default style prefix.

## Style System: Meta Prompting

The best way to ensure style consistency is **meta prompting** — extracting the "style DNA" from one good reference asset, then using that exact prompt for all subsequent generations with only the `[SUBJECT]` swapped.

### How it works

1. Generate or find one "hero asset" that nails the visual style you want
2. Send it to Gemini text model to reverse-engineer the prompt
3. Save the extracted prompt as `style-prompt.txt` in the asset root
4. Every subsequent generation uses this prompt, replacing `[SUBJECT]` only

### Why meta prompting beats alternatives

| Approach | Consistency | Token cost | Reliability |
|---|---|---|---|
| Fixed text prefix (old approach) | Medium — AI interprets loosely | Low | Medium |
| Reference image every call | High — but AI may reinterpret | Very High (~2MB/call) | Medium |
| **Meta prompt (current)** | **High — exact reproduction** | **Low (264 chars)** | **High** |
| Fine-tuned model (Scenario.gg) | Highest | Setup cost | Highest |

### Default style prefix (fallback)

If no `style-prompt.txt` exists yet (first run / init), use this as the initial generation prompt:

```
Gather Town / Habbo Hotel style pixel art game asset, isometric 3/4 view, bright cheerful warm colors, clean pixel outlines, highly detailed pixel art
```

Then extract the meta prompt from the first successful generation.

## Background Instruction (always appended)

Regardless of meta prompt, ALWAYS append this to every generation prompt:

```
on a solid bright magenta #FF00FF background. The ENTIRE background must be exactly #FF00FF magenta, with NO gradients or shadows on the background. ONLY the single isolated object, nothing else in the scene.
```

This is required by the HSL chroma-key removal pipeline. Magenta (#FF00FF) is the game industry standard chroma-key color — it never appears in natural pixel art palettes.

## Perspective

- **Angle**: Isometric ¾ top-down view (~30° from horizontal)
- **Camera**: Looking from bottom-left toward top-right
- **Shadow direction**: Bottom-right, short and crisp
- **Light source**: Top-left (consistent with shadow direction)

## Proportions (relative to character height)

| Element | Relative size | Notes |
|---|---|---|
| Character (standing) | 1.0x | Reference unit |
| Character (sitting) | 0.7x | At desk |
| Desk | 0.5x height, 1.2x width | With monitor, wider than tall |
| Chair | 0.4x | Office swivel chair |
| Bookshelf | 1.2x | Taller than character |
| Door | 1.5x | Tallest common furniture |
| Floor plant | 0.8-1.0x | Varies by type |
| Desk plant | 0.2x | Small succulent/cactus |
| Wall decoration | 0.3-0.5x | Clock, picture frame |
| Bean bag | 0.4x height, 0.8x width | Wide and low |
| Kit (pet) | 0.5x | Smaller than character |

## Color palette guidelines

- **Warm base**: Browns, beiges, warm grays for furniture and floors
- **Department accents**: Orange (Research), Green (Engineering), Blue (Growth), Purple (Ops)
- **Skin tones**: Varied, warm undertones
- **Outlines**: Dark brown or black, 1-2px, clean and consistent
- **Highlights**: Top-left facing surfaces lighter
- **Shadows**: Bottom-right facing surfaces darker, 2-3 tone steps

## Per-category prompt templates

### tile
```
{STYLE_PREFIX}. A single isometric {description} tile, 64x64 pixel grid aligned, seamlessly tileable. {BG_SUFFIX}
```

### furniture
```
{STYLE_PREFIX}. A single {description}. Isometric perspective, detailed with visible texture and shading. {BG_SUFFIX}
```

### character
```
{STYLE_PREFIX}. A single cute office worker character, {description}. Gather Town style proportions: blocky square head wider than body, dot eyes with white highlight, small body. {BG_SUFFIX}
```

### pet
```
{STYLE_PREFIX}. A single small cute {description}. Expressive face, big eyes, stubby limbs. Game mascot style. {BG_SUFFIX}
```

### decoration
```
{STYLE_PREFIX}. A single {description}. Small decorative object, detailed pixel art. {BG_SUFFIX}
```

### background
```
{STYLE_PREFIX}. A wide panoramic {description}. Suitable as a background layer, horizontally tileable or wide format. {BG_SUFFIX}
```

## Predefined asset batches

### tile
| name | description |
|------|-------------|
| floor-wood | wooden floor tile with warm wood grain texture |
| floor-carpet-orange | orange carpet tile for Research department |
| floor-carpet-green | green carpet tile for Engineering department |
| floor-carpet-blue | blue carpet tile for Growth department |
| floor-carpet-purple | purple carpet tile for Ops department |
| wall-back | cream/beige back wall section |
| wall-side | slightly darker side wall section |

### furniture
| name | description |
|------|-------------|
| desk-basic | wooden office desk with computer monitor, keyboard, mouse, and coffee mug |
| desk-standing | modern standing desk with large monitor and adjustable height |
| chair-office | dark office swivel chair with armrests |
| bookshelf | tall wooden bookshelf packed with colorful books, small plant on top |
| whiteboard | office whiteboard covered in colorful sticky notes, marker tray at bottom |
| beanbag-green | large green bean bag chair, puffy and round |
| beanbag-orange | large orange bean bag chair, puffy and round |
| beanbag-purple | large purple bean bag chair, puffy and round |
| coffee-station | espresso machine on wooden counter with white mug underneath |
| water-cooler | water cooler dispenser with blue water jug on top |
| meeting-table | round meeting table with 4 small chairs |
| sofa | comfortable modern office couch |

### character
| name | description |
|------|-------------|
| char-research-sitting | in orange shirt, brown hair, sitting and typing on laptop |
| char-research-standing | in orange shirt, brown hair, standing casually |
| char-engineering-sitting | in green shirt, black hair, sitting and typing on laptop |
| char-engineering-standing | in green shirt, black hair, standing casually |
| char-growth-sitting | in blue shirt, blonde hair, sitting and typing on laptop |
| char-growth-standing | in blue shirt, blonde hair, standing casually |
| char-ops-sitting | in purple shirt, red ponytail, sitting and typing on laptop |
| char-ops-standing | in purple shirt, red ponytail, standing casually |

### pet
| name | description |
|------|-------------|
| kit-idle | golden yellow cat creature mascot, happy expression, standing still |
| kit-bounce-1 | golden yellow cat creature mascot, jumping up with arms raised |
| kit-bounce-2 | golden yellow cat creature mascot, at peak of jump |
| kit-blink | golden yellow cat creature mascot, eyes closed, smiling |

### decoration
| name | description |
|------|-------------|
| plant-hanging | hanging potted plant with green vines draping from terracotta pot on chain |
| plant-floor-large | tall floor potted plant with large green leaves in brown pot |
| plant-desk | small succulent in tiny pot for desk |
| clock-wall | round wall clock with simple markers |
| picture-frame | framed picture/certificate for wall |
| pendant-light | hanging ceiling pendant light with warm glow |
| window-large | large floor-to-ceiling window panel |
| bulletin-board | cork board with pinned papers and photos |

### background
| name | description |
|------|-------------|
| skyline-day | city skyline with buildings, blue sky, white clouds, wide panorama |
| skyline-night | nighttime city skyline with lit windows, dark blue sky, wide panorama |
