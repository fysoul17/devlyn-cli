---
name: asset-creator
description: >
  Generate consistent pixel art game assets using AI image generation + meta-prompting
  for style lock + HSL chroma-key background removal. Produces transparent PNGs ready
  for PixiJS, Phaser, or any 2D game engine. Use when building pixel art games, creating
  game sprites, generating isometric assets, making character sprites, or when user says
  "create asset", "generate sprite", "make game art", "pixel art asset", or "에셋 만들어".
allowed-tools: Read, Grep, Glob, Edit, Write, Bash
argument-hint: "[category] [name] \"[description]\" or batch [category] or list or init"
---

# Asset Creator — AI-Powered Game Asset Pipeline

Generate production-ready pixel art game assets with consistent style, transparent backgrounds, and catalog metadata.

Reference files in this skill directory:
- `STYLE-GUIDE.md` — Art direction defaults, per-category templates, predefined asset batches
- `CATALOG-SCHEMA.md` — manifest.json structure and marketplace metadata

## Pipeline overview

```
0. STYLE LOCK    Meta-prompt one reference asset → extract style DNA (once per project)
1. GENERATE      Swap [SUBJECT] in meta prompt → Gemini 3.0 Pro Image
2. BG REMOVE     HSL flood fill (Pillow) — magenta + near-white removal
3. NORMALIZE     Auto-crop + category-based size normalization
4. CATALOG       manifest.json auto-registration with marketplace metadata
```

This pipeline was validated through iterative testing. The meta-prompting approach extracts the "style DNA" from one good asset and replicates it precisely — more consistent than reference images (which the AI may reinterpret) and more token-efficient (264 chars vs 2MB image per call).

## Prerequisites

```bash
# Python 3 with Pillow — required for HSL background removal
python3 -c "from PIL import Image; print('OK')"

# API key — required for AI image generation
grep GEMINI_API_KEY .env
```

ImageMagick is NOT required — the pipeline uses pure Python (Pillow) for background removal.

## Usage

```
/asset-creator init                              — Set up project + extract meta prompt from reference
/asset-creator [category] [name] "[description]"  — Generate one asset
/asset-creator batch [category]                   — Generate all predefined assets in a category
/asset-creator list                               — Show current asset inventory
/asset-creator gallery                            — Generate visual review HTML
```

## Workflow

### Parse the command

Read `$ARGUMENTS` and determine the mode:

| Input | Mode | Action |
|---|---|---|
| `init` | **Init** | Set up directories + extract meta prompt from reference asset |
| `[category] [name] "[desc]"` | **Single** | Generate one asset |
| `batch [category]` | **Batch** | Generate all predefined assets for category |
| `list` | **List** | Show asset inventory from manifest.json |
| `gallery` | **Gallery** | Generate review HTML |
| Empty | **Interactive** | Ask what to create |

Valid categories: `tile`, `furniture`, `character`, `pet`, `decoration`, `background`

### Step 0: Style Lock (init mode, or first run)

This is the foundation of style consistency. Run once per project.

**If no meta prompt exists** (`{asset-root}/style-prompt.txt` missing):

1. Check if the project has a reference asset. If not, generate one "hero asset" (a character or prominent furniture piece) using the default style from `STYLE-GUIDE.md`.

2. Send the reference asset to Gemini for meta-prompt extraction:

```python
# Send image + extraction prompt to Gemini (text model, not image gen)
prompt = """Look at this pixel art game asset. Reverse-engineer the EXACT image 
generation prompt that would recreate this STYLE. Replace the specific subject 
with [SUBJECT]. Capture: pixel density, outline thickness, shading technique, 
color palette warmth, perspective angle, proportions, and the solid magenta 
#FF00FF background. Output ONLY the prompt text, max 3 sentences, be precise."""
```

Use `gemini-2.5-flash` (text model) for extraction — it's fast and cheap. NOT the image model.

3. Save the extracted meta prompt to `{asset-root}/style-prompt.txt`.

4. **Validate**: Generate a test asset using the meta prompt. Show it to the user alongside the reference. If the style matches, the meta prompt is locked. If not, regenerate with adjusted extraction prompt.

**If meta prompt exists**: Read `{asset-root}/style-prompt.txt` and use it for all generation.

### Step 1: Locate project asset directory

Look for existing asset directories in order:
1. `dashboard/public/assets/office/` (Pyx Org)
2. `public/assets/game/` (generic game)
3. `assets/` (fallback)

If none exists, create:
```
{asset-root}/
├── tiles/
├── furniture/
├── characters/
├── pets/
├── decorations/
├── backgrounds/
├── raw/              # AI originals (magenta bg, never delete)
├── manifest.json
└── style-prompt.txt  # Meta prompt (style DNA)
```

### Step 2: Generate the asset

Read the meta prompt from `{asset-root}/style-prompt.txt`.

Construct the final prompt by replacing `[SUBJECT]`:
```
{meta_prompt with [SUBJECT] replaced by user's description}

Generate a pixel art IMAGE.
```

Call Gemini 3.0 Pro Image API (`gemini-3-pro-image-preview`):

```python
import json, base64, urllib.request

api_key = os.environ.get("GEMINI_API_KEY") or read_from_dotenv()

payload = {
    "contents": [{"parts": [{"text": full_prompt}]}],
    "generationConfig": {
        "responseModalities": ["IMAGE", "TEXT"],
        "temperature": 0.3
    }
}

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent?key={api_key}"
req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                             headers={"Content-Type": "application/json"}, method="POST")

with urllib.request.urlopen(req, timeout=120) as resp:
    result = json.loads(resp.read().decode())

# Extract image from response
for part in result["candidates"][0]["content"]["parts"]:
    if "inlineData" in part:
        data = base64.b64decode(part["inlineData"]["data"])
        with open(f"{asset_root}/raw/{name}.jpg", "wb") as f:
            f.write(data)
        break
```

### Step 3: Remove background (HSL flood fill)

This is the optimized approach — uses HSL color space instead of RGB for robust chroma-key removal that handles JPG compression artifacts.

```python
from PIL import Image
import colorsys
from collections import deque

def remove_background(input_path, output_path):
    img = Image.open(input_path).convert("RGBA")
    pixels = img.load()
    w, h = img.size

    def should_remove(r, g, b):
        rn, gn, bn = r/255.0, g/255.0, b/255.0
        h_val, l_val, s_val = colorsys.rgb_to_hls(rn, gn, bn)
        hue_deg = h_val * 360
        # Magenta hue range (robust against JPG compression)
        if 250 <= hue_deg <= 340 and s_val > 0.2:
            return True
        # Near-white (catches desaturated magenta from JPG artifacts)
        if r > 230 and g > 230 and b > 230:
            return True
        # Very light + low saturation
        if l_val > 0.9 and s_val < 0.15:
            return True
        return False

    # Phase 1: Flood fill from all edges (only removes connected background)
    visited = set()
    queue = deque()
    for x in range(w):
        queue.append((x, 0)); queue.append((x, h-1))
    for y in range(h):
        queue.append((0, y)); queue.append((w-1, y))

    while queue:
        x, y = queue.popleft()
        if (x, y) in visited or x < 0 or x >= w or y < 0 or y >= h:
            continue
        visited.add((x, y))
        r, g, b, a = pixels[x, y]
        if should_remove(r, g, b):
            pixels[x, y] = (0, 0, 0, 0)
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)]:
                nx, ny = x+dx, y+dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                    queue.append((nx, ny))

    # Phase 2: Edge cleanup (remove remaining pink fringe)
    for y in range(1, h-1):
        for x in range(1, w-1):
            r, g, b, a = pixels[x, y]
            if a == 0: continue
            rn, gn, bn = r/255.0, g/255.0, b/255.0
            h_val, l_val, s_val = colorsys.rgb_to_hls(rn, gn, bn)
            hue_deg = h_val * 360
            if (250 <= hue_deg <= 340 and s_val > 0.1) or (l_val > 0.85 and s_val < 0.2):
                for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    if pixels[x+dx, y+dy][3] == 0:
                        pixels[x, y] = (0, 0, 0, 0)
                        break

    # Auto-crop to content
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    img.save(output_path)
    return img.size
```

Why HSL instead of RGB:
- JPG compression shifts RGB values but barely affects Hue
- Magenta has a distinctive hue (~300°) that's stable across compression levels
- Saturation check prevents false positives on gray/white pixels
- Flood fill from edges ensures interior light pixels are preserved

### Step 4: Register in manifest

Read `{asset-root}/manifest.json`. Get dimensions from the processed PNG. Add entry:

```json
{
  "{category}/{name}": {
    "file": "{category}/{name}.png",
    "category": "{category}",
    "width": W,
    "height": H,
    "anchorX": 0.5,
    "anchorY": 1.0,
    "tags": ["inferred", "from", "description"],
    "theme": "default",
    "tier": "free",
    "price": 0
  }
}
```

See `CATALOG-SCHEMA.md` for full field reference and anchor conventions.

### Step 5: Show result

Display the generated PNG using the Read tool. Report:
- File path and size
- Dimensions (W × H)
- Category, tags, tier
- Manifest status

If unsatisfied, offer to regenerate with an adjusted subject description.

## Batch Mode

Read predefined asset lists from `STYLE-GUIDE.md`. Generate each sequentially with 1.5s delay (rate limiting). Show progress. Generate gallery at end.

## List Mode

Read manifest.json, group by category, display inventory table with dimensions, tier, and file size.

## Gallery Mode

Generate `{asset-root}/gallery.html` showing all assets on checkered transparency background, grouped by category. Suggest `python3 -m http.server 8888` to view.

## Adapting to other AI generators

The pipeline is model-agnostic. To swap generators:
1. Replace the API call in Step 2
2. Keep the meta prompt + magenta background instruction
3. HSL background removal works identically regardless of source
4. If your model outputs PNG with native transparency, skip Step 3
