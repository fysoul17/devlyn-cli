# Asset Catalog Schema

The manifest.json file catalogs all generated assets with metadata that supports both runtime rendering and future marketplace features.

## manifest.json structure

```json
{
  "version": "1.0",
  "style": "gather-town",
  "generatedWith": "gemini-3-pro-image-preview",
  "assets": {
    "furniture/desk-basic": {
      "file": "furniture/desk-basic.png",
      "category": "furniture",
      "width": 765,
      "height": 746,
      "anchorX": 0.5,
      "anchorY": 1.0,
      "tags": ["workspace", "desk", "monitor"],
      "theme": "default",
      "tier": "free",
      "price": 0,
      "animation": null
    },
    "characters/char-research-sitting": {
      "file": "characters/char-research-sitting.png",
      "category": "character",
      "width": 342,
      "height": 500,
      "anchorX": 0.5,
      "anchorY": 1.0,
      "tags": ["research", "sitting", "typing"],
      "theme": "default",
      "tier": "free",
      "price": 0,
      "animation": {
        "frameWidth": 342,
        "frameCount": 1,
        "fps": 0
      }
    }
  }
}
```

## Field reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | string | yes | Relative path from asset root |
| `category` | enum | yes | `tile`, `furniture`, `character`, `pet`, `decoration`, `background` |
| `width` | number | yes | Pixel width after trim |
| `height` | number | yes | Pixel height after trim |
| `anchorX` | number | yes | 0-1, horizontal anchor for positioning (0.5 = center) |
| `anchorY` | number | yes | 0-1, vertical anchor (1.0 = bottom for isometric depth sort) |
| `tags` | string[] | yes | Searchable keywords |
| `theme` | string | yes | Theme pack ID (`"default"`, `"cyberpunk"`, `"nature"`, etc.) |
| `tier` | enum | yes | `"free"`, `"premium"`, `"exclusive"` |
| `price` | number | yes | 0 for free, positive integer for paid (currency unit TBD) |
| `animation` | object\|null | no | Spritesheet info if animated |

## Animation field

For spritesheet assets (multiple frames in one image):

```json
{
  "frameWidth": 64,
  "frameCount": 4,
  "fps": 8
}
```

The renderer reads left-to-right, each frame `frameWidth` pixels wide, cycling at `fps` frames per second.

## Anchor conventions

| Asset type | anchorX | anchorY | Reason |
|------------|---------|---------|--------|
| Most assets | 0.5 | 1.0 | Bottom-center — standard for isometric depth sorting |
| Ceiling items (lights, plants) | 0.5 | 0.0 | Top-center — hangs from above |
| Wall items (clock, frame) | 0.5 | 0.5 | Center — placed on wall surface |
| Floor tiles | 0.5 | 0.5 | Center — aligned to grid |

## Theme packs

A theme is a set of assets that share a visual style. The `"default"` theme ships free with the product. Premium themes are sold as packs.

```
assets/
├── themes/
│   ├── default/     → symlinks or copies of base assets
│   ├── cyberpunk/   → neon-tinted variants
│   ├── nature/      → wood-and-leaf variants
│   └── cozy-night/  → warm lamp-lit variants
```

When a user switches themes, the renderer swaps asset paths: `furniture/desk-basic.png` → `themes/cyberpunk/desk-basic.png`. Assets not overridden by the theme fall back to `default`.
