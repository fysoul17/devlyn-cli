# Image Sourcing

Strategies for sourcing images to fill template fields requiring photos, logos, signatures, or illustrations.

## Image Types

| image_type | Description | Auto-generate? |
|-----------|-------------|----------------|
| `photo` | ID/profile pictures | No — user-provided only |
| `logo` | Company logos | No — user-provided only |
| `signature` | Signature fields | NEVER — must be user-provided |
| `figure` | Illustrations, diagrams | Yes — auto-generated during fill |

## Sourcing Priority

### 1. Check Ingested Sources
Search `.dokkit/sources/` for image files (PNG, JPG, JPEG, BMP, TIFF):
- Match by field's `image_type` and source metadata
- Set `image_source: "ingested"` and `image_file` to the path

### 2. User-Provided File
Via `/dokkit modify "use <file>"`:
- Search `.dokkit/sources/`, then project root
- Copy to `.dokkit/images/`

### 3. AI Generation
```bash
python .claude/skills/dokkit/scripts/source_images.py generate \
  --prompt "인포그래픽: AI 감정 케어 플랫폼 4단계 로드맵" \
  --preset infographic \
  --output-dir .dokkit/images/ \
  --project-dir . \
  --lang ko
```
Parse `__RESULT__` JSON from stdout: `{"image_id": "...", "file_path": "...", "source_type": "generated"}`

#### Language Options (`--lang`)

| Value | Behavior | Example |
|---|---|---|
| `ko` | **Default.** All text in Korean only. English strictly forbidden. | 제목, 라벨, 설명 모두 한국어 |
| `en` | All text in English only. | Titles, labels, descriptions in English |
| `ko+en` | Mixed. Titles in Korean, technical terms may use English. | 제목은 한국어, Node.js 등 기술 용어는 영어 허용 |
| `ja` | All text in Japanese only. | 日本語のみ |
| `<code>` | Any ISO 639-1 code. | `zh`, `es`, `fr`, `de`, `pt` |
| `<a>+<b>` | Mixed: primary + secondary language. | `ko+ja`, `en+ko` |

#### Presets

| Preset | Style | Default Aspect Ratio |
|---|---|---|
| `technical_illustration` | Clean diagrams, labeled components | 16:9 |
| `infographic` | Icon-based, corporate color palette | 16:9 |
| `photorealistic` | High-quality, natural lighting | 4:3 |
| `concept` | Abstract/modern, business proposal style | 1:1 |
| `chart` | Clean data visualization | 16:9 |

Use `--aspect-ratio 16:9` to override. Use `--no-enhance` to skip preset style injection (language instruction still applies).

**Model**: `gemini-3-pro-image-preview` (nano-banana). Best for accurate text rendering in non-Latin scripts.

### 4. Web Search
```bash
python .claude/skills/dokkit/scripts/source_images.py search \
  --query "company logo example" \
  --output-dir .dokkit/images/
```
Parse `__RESULT__` JSON: `{"image_id": "...", "file_path": "...", "source_type": "searched"}`
(Note: search is not yet implemented — directs user to provide images manually.)

## Prompt Templates by Image Type

| image_type | Suggested prompt |
|-----------|-----------------|
| photo | "Professional ID photo, white background, formal attire" |
| logo | "Clean company logo, transparent background, modern design" |
| signature | **NEVER generate** — signatures must be user-provided |
| figure | Derive from field label and section context |

## Section Content Image Generation

For `image_opportunities` in `section_content` fields — auto-generated during `/dokkit fill` (decorative/explanatory, not identity-sensitive).

### Prompt Templates by Content Type

| content_type | preset | Prompt guidance |
|---|---|---|
| diagram | `technical_illustration` | "Technical architecture/system diagram showing [concept]. Clean lines, labeled components." |
| flowchart | `technical_illustration` | "Process flowchart showing [steps]. Left-to-right flow, clear arrows, numbered steps." |
| data | `infographic` | "Data visualization showing [metric/trend]. Clean chart style, professional colors." |
| concept | `technical_illustration` | "Conceptual illustration of [idea]. Abstract/modern style, suitable for business proposal." |
| infographic | `infographic` | "Infographic comparing [items]. Icon-based, clean layout, corporate color palette." |

### Dimension Defaults

HWPML units: 1/7200 inch (~283.46 units/mm). ~77% of A4 text width = 36,000 units.

| content_type | HWPML w x h | Approx mm | EMU cx x cy |
|---|---|---|---|
| diagram | 36,000 x 24,000 | 127x85 | 4,572,000 x 3,048,000 |
| flowchart | 36,000 x 24,000 | 127x85 | 4,572,000 x 3,048,000 |
| data | 36,000 x 20,000 | 127x71 | 4,572,000 x 2,540,000 |
| concept | 28,000 x 28,000 | 99x99 | 3,556,000 x 3,556,000 |
| infographic | 36,000 x 24,000 | 127x85 | 4,572,000 x 3,048,000 |

## Default Cell-Level Dimensions

| image_type | Width (mm) | Height (mm) | Width (EMU) | Height (EMU) |
|-----------|-----------|------------|------------|-------------|
| photo | 35 | 45 | 1,260,000 | 1,620,000 |
| logo | 50 | 50 | 1,800,000 | 1,800,000 |
| signature | 40 | 15 | 1,440,000 | 540,000 |
| figure | 100 | 75 | 3,600,000 | 2,700,000 |

Conversion: 1 mm = 36,000 EMU. For HWPX, use HWPML unit system.

## Rules

- Signatures MUST be user-provided — never generate or search
- Never auto-generate/download images without user approval EXCEPT section content images (auto-generated during fill)
- Ingested images can be inserted automatically
- Prefer user-provided over generated
- Image format must be PNG or JPG (compatible with both DOCX and HWPX)

## References

See `references/image-xml-patterns.md` for complete DOCX/HWPX image element structures, registration patterns, and the `build_hwpx_pic_element()` function.
