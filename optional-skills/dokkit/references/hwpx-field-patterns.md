# HWPX Field Detection Patterns

## Pattern 1: Empty Table Cell

Korean forms are heavily table-based. The most common pattern:

```xml
<hp:tr>
  <hp:tc>
    <!-- Label cell -->
    <hp:p>
      <hp:run>
        <hp:rPr charPrIDRef="1"/>
        <hp:t>성명</hp:t>
      </hp:run>
    </hp:p>
  </hp:tc>
  <hp:tc>
    <!-- Empty value cell → FILL THIS -->
    <hp:p>
      <hp:lineseg/>
    </hp:p>
  </hp:tc>
</hp:tr>
```

**Action**: Insert a new `<hp:run>` with `<hp:t>value</hp:t>` into the empty paragraph. Copy `charPrIDRef` from label cell's run.

## Pattern 2: Placeholder Text in Cell

```xml
<hp:tc>
  <hp:p>
    <hp:run>
      <hp:t>(이름을 입력하세요)</hp:t>  <!-- Instruction text -->
    </hp:run>
  </hp:p>
</hp:tc>
```

**Action**: Replace the text in `<hp:t>` with the actual value.

## Pattern 3: Multi-Row Spanning Label

Korean forms often have a label cell spanning multiple rows:

```xml
<hp:tr>
  <hp:tc>
    <hp:cellSpan rowSpan="3"/>
    <hp:p><hp:run><hp:t>학력</hp:t></hp:run></hp:p>
  </hp:tc>
  <hp:tc><hp:p><hp:run><hp:t>학교명</hp:t></hp:run></hp:p></hp:tc>
  <hp:tc><hp:p/></hp:tc>  <!-- Empty → fill with school name -->
</hp:tr>
```

**Action**: The spanning label ("학력" = Education) is the section. Sub-labels ("학교명" = School Name) identify individual fields.

## Pattern 4: Date Fields

```xml
<hp:tc>
  <hp:p>
    <hp:run><hp:t>년</hp:t></hp:run>  <!-- Year -->
  </hp:p>
</hp:tc>
<hp:tc>
  <hp:p>
    <hp:run><hp:t>월</hp:t></hp:run>  <!-- Month -->
  </hp:p>
</hp:tc>
<hp:tc>
  <hp:p>
    <hp:run><hp:t>일</hp:t></hp:run>  <!-- Day -->
  </hp:p>
</hp:tc>
```

**Action**: Fill the cells preceding 년/월/일 with the appropriate date components.

## Pattern 5: Writing Tip Box (작성 팁)

Standalone 1×1 tables with DASH-bordered cells that contain `※` guidance text. These are NOT fillable fields — they must be **deleted** before or during filling.

```xml
<hp:tbl rowCnt="1" colCnt="1">
  <hp:tr>
    <hp:tc borderFillIDRef="16">
      <hp:p>
        <hp:run>
          <hp:rPr charPrIDRef="45"/>          <!-- Often RED style -->
          <hp:t>※ 작성 팁: 사업의 목적과 필요성을 구체적으로 작성하세요.</hp:t>
        </hp:run>
      </hp:p>
      <hp:p>
        <hp:run>
          <hp:rPr charPrIDRef="45"/>
          <hp:t>※ 관련 법령이나 정책 근거를 제시하면 좋습니다.</hp:t>
        </hp:run>
      </hp:p>
    </hp:tc>
  </hp:tr>
</hp:tbl>
```

**Identifying traits**:
- `rowCnt="1"` and `colCnt="1"` (single-cell table)
- `borderFillIDRef` resolves to DASH border style in `header.xml`
- Text starts with `※` or contains `작성 팁`, `작성요령`, `작성 요령`
- Often appears inside a `<hp:subList>` within another table cell

**Two container types**:
- **Standalone**: Top-level 1×1 table between other content → delete the entire `<hp:tbl>`
- **Nested**: Inside a `<hp:subList>` within a fill-target cell → delete the `<hp:subList>` element

**Action**: Flag as `field_type: "tip_box"`, `action: "delete"`. The filler agent removes these before filling.

## Pattern 6: Character Property Resolution (charPrIDRef)

HWPX text formatting is controlled by `charPrIDRef` attributes that reference `<hh:charPr>` entries in `header.xml`.

### How charPrIDRef works
```xml
<!-- In section*.xml — a run references charPr ID 45 -->
<hp:run>
  <hp:rPr charPrIDRef="45"/>
  <hp:t>Some text</hp:t>
</hp:run>

<!-- In header.xml — charPr ID 45 defines the style -->
<hh:charPr id="45" height="1000" textColor="#FF0000"
           bold="false" italic="true" spacing="-5"/>
```

### Template guide text uses RED styles
Many templates use red (#FF0000) charPrIDRef values for guide text, tip boxes, and instructions. Common red IDs seen in Korean government templates: 39, 45, 51, 52, 57, 62, 81.

**Critical rule**: When filling a field, NEVER copy `charPrIDRef` from guide/tip text. Instead, find or create a black (#000000) charPr.

### Finding a suitable black charPr
```python
import xml.etree.ElementTree as ET

def find_black_charpr(header_path):
    """Find a charPrIDRef suitable for filled text (black, normal style)."""
    hns = {"hh": "http://www.hancom.co.kr/hwpml/2011/head"}
    tree = ET.parse(header_path)
    root = tree.getroot()

    candidates = []
    for cp in root.iter("{%s}charPr" % hns["hh"]):
        color = cp.get("textColor", "#000000")
        bold = cp.get("bold", "false")
        italic = cp.get("italic", "false")
        spacing = int(cp.get("spacing", "0"))

        # Want: black text, not italic, non-negative spacing
        if color.upper() in ("#000000", "#000000FF", "black") and \
           italic == "false" and spacing >= 0:
            candidates.append({
                "id": cp.get("id"),
                "bold": bold == "true",
                "height": int(cp.get("height", "1000")),
                "spacing": spacing,
            })

    # Prefer non-bold, standard size, zero spacing
    normal = [c for c in candidates if not c["bold"] and c["spacing"] == 0]
    bold_list = [c for c in candidates if c["bold"] and c["spacing"] == 0]

    return {
        "normal": normal[0]["id"] if normal else None,
        "bold": bold_list[0]["id"] if bold_list else None,
    }
```

### Creating a new charPr if needed
If no suitable black charPr exists in `header.xml`, create one by appending a new `<hh:charPr>` element with the next available ID, `textColor="#000000"`, `bold="false"`, `italic="false"`, `spacing="0"`.

## Pattern 7: Image Field in Table Cell

A label cell containing image-related keywords (사진, 증명사진, 로고, 서명, 직인, 사업자등록증) next to an empty cell indicates an image insertion point.

```xml
<hp:tr>
  <hp:tc>
    <!-- Label cell with image keyword -->
    <hp:p>
      <hp:run>
        <hp:rPr charPrIDRef="1"/>
        <hp:t>사진</hp:t>
      </hp:run>
    </hp:p>
  </hp:tc>
  <hp:tc>
    <!-- Empty cell → INSERT IMAGE HERE -->
    <hp:p>
      <hp:lineseg/>
    </hp:p>
  </hp:tc>
</hp:tr>
```

**Action**: Insert a `<hp:pic>` element INSIDE a `<hp:run>` within the cell's `<hp:p>`. The `<hp:t/>` goes AFTER the pic inside the run.

### Image Paragraph Structure (CRITICAL)

```xml
<!-- pic must be INSIDE run, t/ AFTER pic (matches real Hancom Office output) -->
<hp:p id="..." paraPrIDRef="..." styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
  <hp:linesegarray>
    <hp:lineseg textpos="0" vertpos="0" vertsize="{H}" textheight="{H}"
                baseline="{H*0.85}" spacing="500" .../>
  </hp:linesegarray>
  <hp:run charPrIDRef="0">
    <hp:pic id="{seq_id}" zOrder="{z}" ...>...</hp:pic>
    <hp:t/>
  </hp:run>
</hp:p>
```

### Complete `<hp:pic>` Structure (Hancom Canonical Order)

```xml
<hp:pic id="{seq_id}" zOrder="{z}" numberingType="PICTURE" textWrap="TOP_AND_BOTTOM"
        textFlow="BOTH_SIDES" lock="0" dropcapstyle="None"
        href="" groupLevel="0" instid="{seq_id}" reverse="0">
  <!-- Group 1: Geometry -->
  <hp:offset x="0" y="0"/>
  <hp:orgSz width="{W}" height="{H}"/>
  <hp:curSz width="{W}" height="{H}"/>
  <hp:flip horizontal="0" vertical="0"/>
  <hp:rotationInfo angle="0" centerX="{W/2}" centerY="{H/2}" rotateimage="1"/>
  <hp:renderingInfo>
    <hc:transMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>
    <hc:scaMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>
    <hc:rotMatrix e1="1" e2="-0" e3="0" e4="0" e5="1" e6="0"/>
  </hp:renderingInfo>
  <!-- Group 2: Image data -->
  <hp:imgRect>
    <hc:pt0 x="0" y="0"/>
    <hc:pt1 x="{W}" y="0"/>
    <hc:pt2 x="{W}" y="{H}"/>
    <hc:pt3 x="0" y="{H}"/>
  </hp:imgRect>
  <hp:imgClip left="0" right="{pixW}" top="0" bottom="{pixH}"/>
  <hp:inMargin left="0" right="0" top="0" bottom="0"/>
  <hp:imgDim dimwidth="{pixW}" dimheight="{pixH}"/>
  <hc:img binaryItemIDRef="{manifest_id}" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/>
  <!-- Group 3: Layout (AFTER hc:img) -->
  <hp:sz width="{W}" widthRelTo="ABSOLUTE" height="{H}" heightRelTo="ABSOLUTE" protect="0"/>
  <hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="0" allowOverlap="0"
          holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN"
          vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>
  <hp:outMargin left="0" right="0" top="0" bottom="0"/>
</hp:pic>
```

Where: `{W}/{H}` = HWPML units (1/7200 inch), `{pixW}/{pixH}` = pixel dimensions from PIL, `{manifest_id}` = `id` from `content.hpf`.

### 9 Critical Rules for `<hp:pic>`

1. **`<img>` uses `hc:` namespace** — `<hc:img>`, NOT `<hp:img>`
2. **`<imgRect>` has 4 `<hc:pt>` children** — `<hc:pt0>` through `<hc:pt3>`, NOT inline attributes
3. **All required children present** — `offset`, `orgSz`, `curSz`, `flip`, `rotationInfo`, `renderingInfo`, `inMargin`
4. **No spurious elements** — Do NOT add `hp:lineShape`, `hp:caption`, `hp:shapeComment`
5. **`imgClip` right/bottom = pixel dims** — from `imgDim`, NOT zeros
6. **Hancom canonical element order** — offset, orgSz, ..., hc:img, **then** sz, pos, outMargin
7. **Register in `content.hpf` manifest only** — Do NOT add `<hh:binDataItems>` to `header.xml`
8. **`hp:pos` attributes** — `flowWithText="0"` `horzRelTo="COLUMN"`
9. **pic INSIDE run, t AFTER pic** — `<hp:run><hp:pic>...</hp:pic><hp:t/></hp:run>`

## Pattern 8: SubList Cell Wrapping (CRITICAL)

In Korean government HWPX templates, ~65% of table cells wrap their content in `<hp:subList>/<hp:p>` rather than having `<hp:p>` as a direct child of `<hp:tc>`. Hancom Office reads content from inside `<hp:subList>` and ignores orphaned direct `<hp:p>` elements.

### Two cell structures

**Direct pattern** (~35% of cells):
```xml
<hp:tc>
  <hp:cellAddr .../>
  <hp:cellSpan .../>
  <hp:cellSz .../>
  <hp:p>
    <hp:run><hp:t>Content here</hp:t></hp:run>
  </hp:p>
</hp:tc>
```

**SubList pattern** (~65% of cells):
```xml
<hp:tc>
  <hp:cellAddr .../>
  <hp:cellSpan .../>
  <hp:cellSz .../>
  <hp:subList>
    <hp:p>
      <hp:run><hp:t>Content here</hp:t></hp:run>
    </hp:p>
  </hp:subList>
</hp:tc>
```

### Critical rule for filling

When writing content into a cell, ALWAYS check for `<hp:subList>` first:
1. If `<hp:subList>` exists: write into `<hp:subList>/<hp:p>`, NOT as a direct `<hp:p>` child of `<hp:tc>`
2. If no `<hp:subList>`: write as direct `<hp:p>` child of `<hp:tc>` (standard pattern)

**Wrong** — creates orphaned paragraphs that Hancom ignores:
```python
# BAD: always writes to cell directly
p = ET.SubElement(cell, hp_tag("p"))
```

**Correct** — respects subList wrapper:
```python
# GOOD: check for subList first
container = cell
for c in cell:
    if c.tag == hp_tag("subList"):
        container = c
        break
p = ET.SubElement(container, hp_tag("p"))
```

This applies to ALL cell operations: `clear_cell_content()`, `fill_cell_text()`, and `insert_cell_image_resolved()`.

## Pattern 9: cellAddr Row Addressing (CRITICAL)

Every `<hp:tc>` inside a `<hp:tr>` contains a `<hp:cellAddr>` element with `colAddr` and `rowAddr` attributes. The `rowAddr` MUST equal the **0-based index** of the `<hp:tr>` within its parent `<hp:tbl>`.

### Structure
```xml
<hp:tbl rowCnt="3" colCnt="2">
  <hp:tr>                                    <!-- row index 0 -->
    <hp:tc>
      <hp:cellAddr colAddr="0" rowAddr="0"/> <!-- rowAddr = 0 ✓ -->
      ...
    </hp:tc>
    <hp:tc>
      <hp:cellAddr colAddr="1" rowAddr="0"/> <!-- rowAddr = 0 ✓ -->
      ...
    </hp:tc>
  </hp:tr>
  <hp:tr>                                    <!-- row index 1 -->
    <hp:tc>
      <hp:cellAddr colAddr="0" rowAddr="1"/> <!-- rowAddr = 1 ✓ -->
      ...
    </hp:tc>
    <hp:tc>
      <hp:cellAddr colAddr="1" rowAddr="1"/> <!-- rowAddr = 1 ✓ -->
      ...
    </hp:tc>
  </hp:tr>
</hp:tbl>
```

### Consequence of violation
If two `<hp:tr>` elements share the same `rowAddr`, Polaris Office **silently hides** the duplicate rows. The table renders with missing data but no error is reported. This is the most common corruption when cloning rows.

### Fix code
```python
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"

def fix_celladdr_rowaddr(tbl):
    """Fix rowAddr values and rowCnt for an HWPX table after row insertion."""
    rows = tbl.findall(f"{{{HP}}}tr")
    for row_idx, tr in enumerate(rows):
        for tc in tr.findall(f"{{{HP}}}tc"):
            cell_addr = tc.find(f"{{{HP}}}cellAddr")
            if cell_addr is not None:
                cell_addr.set("rowAddr", str(row_idx))
    tbl.set("rowCnt", str(len(rows)))
```

### When to apply
- After cloning a `<hp:tr>` and inserting it into a table
- After inserting new rows built from `table_content` pipe-delimited data
- After deleting rows from a table
- Any time the number or order of `<hp:tr>` children changes

## Pattern 10: Image Paragraph Center Alignment

Image paragraphs in HWPX should be center-aligned using a `paraPrIDRef` that references a center-aligned `<hh:paraPr>` from `header.xml`.

### Finding center-aligned paraPrIDRef

```python
def find_center_parapr(header_path):
    """Find first center-aligned paraPr from header.xml for image paragraphs."""
    import xml.etree.ElementTree as ET
    HH = "http://www.hancom.co.kr/hwpml/2011/head"
    tree = ET.parse(header_path)
    for pp in tree.getroot().iter(f"{{{HH}}}paraPr"):
        align = pp.find(f"{{{HH}}}align")
        if align is not None and align.get("horizontal") == "CENTER":
            return pp.get("id")
    return "0"  # fallback to default
```

### Usage in image paragraphs

```xml
<!-- Image paragraph uses center-aligned paraPrIDRef -->
<hp:p id="..." paraPrIDRef="{CENTER_PARAPR_ID}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
  <hp:linesegarray>
    <hp:lineseg textpos="0" vertpos="0" vertsize="{H}" textheight="{H}" .../>
  </hp:linesegarray>
  <hp:run charPrIDRef="0">
    <hp:pic id="{seq_id}" ...>...</hp:pic>
    <hp:t/>
  </hp:run>
</hp:p>
```

### Why this matters

Without center alignment, images default to left-aligned positioning. Korean government document templates expect centered images, particularly for section content images (~77% page width). The `paraPrIDRef` must reference a `<hh:paraPr>` that has `<hh:align horizontal="CENTER"/>`.

### When to apply
- ALL image paragraphs in section content (from `image_opportunities`)
- Cell-level images that should be centered within the cell
- Both standalone and inline image paragraphs

## Safe HWPX Modification

```python
import xml.etree.ElementTree as ET

ns = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
}

# Register namespaces to avoid prefix changes
for prefix, uri in ns.items():
    ET.register_namespace(prefix, uri)

tree = ET.parse("Contents/section0.xml")
root = tree.getroot()

# Find empty cells adjacent to label cells in tables
for tbl in root.iter("{%s}tbl" % ns["hp"]):
    for tr in tbl.iter("{%s}tr" % ns["hp"]):
        cells = list(tr.iter("{%s}tc" % ns["hp"]))
        for i, cell in enumerate(cells):
            # Check if this cell has text (label)
            texts = [t.text for t in cell.iter("{%s}t" % ns["hp"]) if t.text]
            if texts and i + 1 < len(cells):
                next_cell = cells[i + 1]
                next_texts = [t.text for t in next_cell.iter("{%s}t" % ns["hp"]) if t.text]
                if not next_texts:
                    label = "".join(texts)
                    # This is a fillable field with label
                    print(f"Found field: {label}")

tree.write("Contents/section0.xml", xml_declaration=True, encoding="UTF-8")
```
