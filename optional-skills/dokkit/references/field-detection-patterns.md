# Field Detection Patterns

## DOCX Detection Heuristics

### Heuristic 1: Curly Brace Placeholders
```regex
\{\{[^}]+\}\}
```
Match text like `{{field_name}}`. High reliability.

### Heuristic 2: Angle Bracket Placeholders
```regex
<<[^>]+>>
```
Match text like `<<field_name>>`. High reliability.

### Heuristic 3: Square Bracket Placeholders
```regex
\[[^\]]+\]
```
Match text like `[field_name]`. Medium reliability (may match references).

### Heuristic 4: Underline-Only Runs
A run where:
- `<w:rPr>` contains `<w:u w:val="single"/>`
- `<w:t>` contains only spaces, underscores, or is empty
- Run length > 3 characters

### Heuristic 5: Empty Table Cells
A `<w:tc>` that:
- Contains only `<w:p/>` or `<w:p><w:pPr/></w:p>` (empty paragraph)
- Is adjacent to a cell containing text (the label)
- The label cell's text is short (< 50 chars) and not numeric

### Heuristic 6: Instruction Text
A run where text matches patterns like:
```regex
\(.*?(enter|type|input|write|fill|입력).*?\)
```

### Heuristic 7: Content Controls
Any `<w:sdt>` element with `<w:showingPlcHdr/>` in its properties.

### Heuristic 8: Image Fields
A field is classified as `image` when any of these conditions hold:
- A `{{placeholder}}` or `<<placeholder>>` contains an image keyword
- A table cell contains an existing `<w:drawing>` element (pre-positioned image slot)
- An empty table cell is adjacent to a cell whose label matches an image keyword

**Image keywords** (case-insensitive):
- Korean: 사진, 증명사진, 여권사진, 로고, 서명, 날인, 도장, 직인
- English: Photo, Picture, Logo, Signature, Stamp, Seal, Image, Portrait

**Image type classification**:
| Keyword match | `image_type` |
|---------------|-------------|
| 사진, 증명사진, 여권사진, photo, picture, portrait, image | `photo` |
| 로고, logo | `logo` |
| 서명, 날인, 도장, 직인, signature, stamp, seal | `signature` |
| (no keyword match) | `figure` |

Image fields are **excluded** from the `placeholder_text` and `empty_cell` detectors to prevent double-detection.

### Heuristic 9: Tip Box
A `<w:tbl>` that:
- Has exactly one row and one cell (1×1 table)
- `<w:tblBorders>` uses `w:val="dashed"` borders
- Cell text starts with `※` or contains `작성 팁` / `작성요령`
- Often has red text color (`<w:color w:val="FF0000"/>`)

→ `field_type: "tip_box"`, `action: "delete"`

## HWPX Detection Heuristics

### Heuristic 1: Empty Adjacent Cells
Same as DOCX but using `<hp:tc>` and `<hp:t>` elements.

### Heuristic 2: Korean Instruction Text
```regex
\(.*?(입력|기재|작성).*?\)
```

### Heuristic 3: Date Component Cells
Cells immediately before 년/월/일 (year/month/day) markers.

### Heuristic 4: Image Fields
Same logic as DOCX Heuristic 8, adapted for HWPX elements:
- `<hp:pic>` instead of `<w:drawing>`
- `<hp:tc>` / `<hp:t>` instead of `<w:tc>` / `<w:t>`
- Same image keyword list and type classification

### Heuristic 5: Tip Box
An `<hp:tbl>` that:
- Has `rowCnt="1"` and `colCnt="1"` (single-cell table)
- `borderFillIDRef` resolves to DASH border style in `header.xml`
- Cell text starts with `※` or contains `작성 팁` / `작성요령` / `작성 요령`
- May appear standalone or nested inside a `<hp:subList>` within another cell

→ `field_type: "tip_box"`, `action: "delete"`, `container: "standalone"|"nested"`

### Heuristic 6: Section Header Rows
Table rows where:
- First cell spans multiple columns (`hp:cellSpan colSpan > 1`)
- Text is short and descriptive (section name)
- Background may be shaded

## HWPX Pre-Fill Sanitization

### Negative Character Spacing
HWPX templates may define `<hh:charPr>` elements in `header.xml` with negative `<hh:spacing>` values (e.g., `hangul="-3"`). These compress characters closer together, which works for short placeholder text but causes **severe text overlap** when the filler replaces placeholders with longer content.

**Rule**: Before filling, scan ALL `<hh:charPr>` definitions in `header.xml` and set any negative spacing attribute values to `"0"`. This applies to all attributes: `hangul`, `latin`, `hanja`, `japanese`, `other`, `symbol`, `user`.

**Example fix**:
```xml
<!-- Before (causes overlap) -->
<hh:spacing hangul="-3" latin="-3" hanja="-3" japanese="-3" other="-3" symbol="-3" user="-3"/>

<!-- After (normal spacing) -->
<hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
```

## False Positive Filtering

Exclude detected "fields" that are:
- Part of a header/title row (not fillable)
- Copyright notices or footer text
- Page numbers or running headers
- Table of contents entries
- Cross-reference markers
