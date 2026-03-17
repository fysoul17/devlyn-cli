# Section Content Range Detection (HWPX)

## Problem

When `analysis.json` records `element_path: "section/children[N:M]"` for `section_content` fields, those indices refer to the **pre-tip-removal** state of the document. Tip box removal (Phase 2) deletes standalone tip paragraphs from the section root, shifting all subsequent child indices.

Using stale indices causes:
1. **Section titles get destroyed** — the range overlaps title elements
2. **Images don't show** — corrupted document structure
3. **Out-of-bounds errors** — indices exceed actual child count

## Solution: Dynamic Range Detection

After tip removal, **recompute** section content ranges by scanning the section root's children for structural markers (section title elements). This produces correct post-removal indices.

### Algorithm

```python
def find_section_content_ranges(root, hp_ns):
    """Find content ranges for each section_content field by locating title markers.

    Must run AFTER tip box removal so indices are stable.

    Returns dict mapping field IDs to (start, end) inclusive child index ranges.
    """
    hp_tag = lambda name: f'{{{hp_ns}}}{name}'
    children = list(root)
    markers = {}  # label -> child index

    for i, child in enumerate(children):
        text = ''.join(t.text or '' for t in child.iter(hp_tag('t'))).strip()

        # --- Section title markers ---
        # These are hp:p elements containing 1x2 hp:tbl with numbered headings.
        # Match by section number + characteristic keywords.
        # Use flexible matching: number prefix + key Korean terms.

        if '1.' in text and '문제' in text and ('Problem' in text or '필요성' in text):
            markers['sec1_title'] = i
        elif '2.' in text and '실현' in text and ('Solution' in text or '개발' in text):
            markers['sec2_title'] = i
        elif '3.' in text and '성장' in text and ('Scale' in text or '사업화' in text):
            markers['sec3_title'] = i
        elif '4.' in text and '팀' in text and ('Team' in text or '대표자' in text):
            markers['sec4_title'] = i

        # --- End markers (tables/sections that follow the content) ---
        elif '사업추진' in text and '일정' in text and '협약기간' in text:
            markers['schedule1'] = i
        elif '사업추진' in text and '일정' in text and '전체' in text:
            markers['schedule2'] = i
        elif '팀 구성' in text and '구분' in text and '직위' in text:
            markers['team_table'] = i

    # Build ranges: content starts after title, ends before next structural element
    ranges = {}
    if 'sec1_title' in markers and 'sec2_title' in markers:
        ranges['field_028'] = (markers['sec1_title'] + 1, markers['sec2_title'] - 1)
    if 'sec2_title' in markers and 'schedule1' in markers:
        ranges['field_029'] = (markers['sec2_title'] + 1, markers['schedule1'] - 1)
    if 'sec3_title' in markers and 'schedule2' in markers:
        ranges['field_046'] = (markers['sec3_title'] + 1, markers['schedule2'] - 1)
    if 'sec4_title' in markers and 'team_table' in markers:
        ranges['field_051'] = (markers['sec4_title'] + 1, markers['team_table'] - 1)

    return ranges
```

### Integration into fill_template.py

The filler agent MUST include this logic when generating `fill_template.py` for HWPX templates that have `section_content` fields:

```python
# Phase 2b: After tip removal, before filling
# Override stale analysis.json ranges with dynamically-detected correct ranges
dynamic_ranges = find_section_content_ranges(root)
for fid, dyn_range in dynamic_ranges.items():
    if fid in field_refs:
        field_refs[fid] = dyn_range
```

### Adapting for Different Templates

The marker detection patterns above are specific to the 예비창업패키지 사업계획서 template. For other templates:

1. **Identify structural markers** — section title elements that bound each `section_content` field
2. **Match by text content** — use keywords from the section titles that appear in the template
3. **Map field IDs** — connect each `section_content` field's ID from analysis.json to the correct marker pair

The general pattern is always:
- `content_start = title_marker_index + 1`
- `content_end = next_structural_element_index - 1`

### Why Not Fix analysis.json Instead?

The analyzer runs BEFORE tip removal, so it can only record pre-removal indices. The correct approach is:
1. Analyzer records approximate ranges (useful for documentation)
2. Filler dynamically recomputes exact ranges after cleanup

### imgDim: Use Actual Image Dimensions

When inserting images via `hp:pic`, the `hp:imgDim` element should use the **actual pixel dimensions** of the image file, not the display size. Use PIL/Pillow:

```python
from PIL import Image

# Display size (for hp:sz, hp:picRect, hp:imgRect)
img_w = SECTION_IMG_WIDTH   # e.g. 29400
img_h = SECTION_IMG_HEIGHT  # e.g. 16538

# Actual pixel dimensions (for hp:imgDim only)
dim_w, dim_h = img_w, img_h
try:
    with Image.open(image_path) as pil_img:
        dim_w, dim_h = pil_img.size
except Exception:
    pass  # Fall back to display dimensions
```
