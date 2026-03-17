# Image XML Patterns

## DOCX Image Pattern

### Required Namespace Declarations
These namespaces must be present on the root `<w:document>` element:
```xml
xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"
xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
```

### Relationship Entry (word/_rels/document.xml.rels)
```xml
<Relationship
  Id="rId8"
  Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
  Target="media/image1.png"/>
```

### Content_Types Entry ([Content_Types].xml)
Add if the image extension is not already registered:
```xml
<!-- For PNG images -->
<Default Extension="png" ContentType="image/png"/>

<!-- For JPEG images -->
<Default Extension="jpeg" ContentType="image/jpeg"/>
<Default Extension="jpg" ContentType="image/jpeg"/>
```

### Drawing Element (in document.xml)
Wrap in a `<w:r>` element within a paragraph in the target cell:
```xml
<w:r>
  <w:drawing>
    <wp:inline distT="0" distB="0" distL="0" distR="0">
      <wp:extent cx="914400" cy="1219200"/>
      <wp:docPr id="1" name="Picture 1"/>
      <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
        <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
          <pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
            <pic:nvPicPr>
              <pic:cNvPr id="1" name="image1.png"/>
              <pic:cNvPicPr/>
            </pic:nvPicPr>
            <pic:blipFill>
              <a:blip r:embed="rId8"/>
              <a:stretch><a:fillRect/></a:stretch>
            </pic:blipFill>
            <pic:spPr>
              <a:xfrm>
                <a:off x="0" y="0"/>
                <a:ext cx="914400" cy="1219200"/>
              </a:xfrm>
              <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
            </pic:spPr>
          </pic:pic>
        </a:graphicData>
      </a:graphic>
    </wp:inline>
  </w:drawing>
</w:r>
```

## HWPX Image Pattern

### A. Registration — Manifest Only

Images are registered ONLY in `Contents/content.hpf` manifest. Do NOT add `<hh:binDataItems>` to `header.xml`. No entries needed in `META-INF/manifest.xml`.

```xml
<!-- Contents/content.hpf — add <opf:item> for each image -->
<opf:item id="image1" href="BinData/image1.png" media-type="image/png" isEmbeded="1"/>
```

The `id` attribute becomes the `binaryItemIDRef` in the `<hc:img>` element below.

### B. Paragraph Structure (CRITICAL)

Images MUST be placed **inside** the `<hp:run>` element, with `<hp:t/>` **after** the `<hp:pic>`. This matches real Hancom Office output.

```xml
<!-- CORRECT: pic inside run, t after pic -->
<hp:p id="..." paraPrIDRef="..." styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
  <hp:linesegarray>
    <hp:lineseg textpos="0" vertpos="0" vertsize="{H}" textheight="{H}"
                baseline="{H*0.85}" spacing="500" horzpos="0" horzsize="..." flags="393216"/>
  </hp:linesegarray>
  <hp:run charPrIDRef="0">
    <hp:pic ...>...</hp:pic>
    <hp:t/>
  </hp:run>
</hp:p>

<!-- WRONG: pic as sibling of run — images will NOT render -->
<hp:run charPrIDRef="0"><hp:t/></hp:run>
<hp:pic ...>...</hp:pic>
```

### C. Complete `<hp:pic>` Structure (Hancom Canonical Order)

Element order matches real Hancom Office output. Every child element listed is **required**. Do NOT include `<hp:lineShape>` (not present in real Hancom files).

```xml
<hp:pic id="{seq_id}" zOrder="{z}" numberingType="PICTURE" textWrap="TOP_AND_BOTTOM"
        textFlow="BOTH_SIDES" lock="0" dropcapstyle="None"
        href="" groupLevel="0" instid="{seq_id}" reverse="0">
  <!-- Group 1: Geometry (Hancom canonical order) -->
  <hp:offset x="0" y="0"/>
  <hp:orgSz width="{W}" height="{H}"/>
  <hp:curSz width="{W}" height="{H}"/>
  <hp:flip horizontal="0" vertical="0"/>
  <hp:rotationInfo angle="0" centerX="{W_half}" centerY="{H_half}" rotateimage="1"/>
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
  <!-- Group 3: Layout (AFTER hc:img in Hancom canonical order) -->
  <hp:sz width="{W}" widthRelTo="ABSOLUTE" height="{H}" heightRelTo="ABSOLUTE" protect="0"/>
  <hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="0" allowOverlap="0"
          holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN"
          vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>
  <hp:outMargin left="0" right="0" top="0" bottom="0"/>
</hp:pic>
```

**Variable definitions**:
- `{W}` / `{H}` — Display size in HWPML units (1/7200 inch). Use defaults from Size Calculations table or analysis.json dimensions.
- `{W_half}` / `{H_half}` — Half of W/H for rotation center.
- `{pixW}` / `{pixH}` — Actual pixel dimensions from PIL/Pillow `Image.open(path).size`.
- `{manifest_id}` — The `id` attribute from the `<opf:item>` in `content.hpf`.
- `{seq_id}` — Sequential ID: find max existing `id` in section XML + 1.
- `{z}` — zOrder: find max existing `zOrder` in section XML + 1.

### D. Python `build_hwpx_pic_element()` Function

```python
import xml.etree.ElementTree as ET
from PIL import Image

HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HC = "http://www.hancom.co.kr/hwpml/2011/core"

def build_hwpx_pic_element(
    manifest_id: str,
    image_path: str,
    width_hwpml: int,
    height_hwpml: int,
    seq_id: int,
    z_order: int,
) -> ET.Element:
    """Build a complete <hp:pic> element for HWPX image insertion.
    Uses Hancom canonical element order (verified against real Hancom Office output).

    Args:
        manifest_id: The id from content.hpf <opf:item> (e.g. "image1")
        image_path: Path to the image file (for reading pixel dimensions)
        width_hwpml: Display width in HWPML units (1/7200 inch)
        height_hwpml: Display height in HWPML units (1/7200 inch)
        seq_id: Sequential element ID (max existing + 1)
        z_order: Z-order value (max existing + 1)
    """
    with Image.open(image_path) as img:
        pix_w, pix_h = img.size

    W = str(width_hwpml)
    H = str(height_hwpml)
    W_half = str(width_hwpml // 2)
    H_half = str(height_hwpml // 2)
    pixW = str(pix_w)
    pixH = str(pix_h)
    sid = str(seq_id)

    pic = ET.Element(f"{{{HP}}}pic", {
        "id": sid, "zOrder": str(z_order), "numberingType": "PICTURE",
        "textWrap": "TOP_AND_BOTTOM", "textFlow": "BOTH_SIDES", "lock": "0",
        "dropcapstyle": "None", "href": "", "groupLevel": "0",
        "instid": sid, "reverse": "0",
    })

    # Hancom canonical order: offset, orgSz, curSz, flip, rotationInfo,
    # renderingInfo, imgRect, imgClip, inMargin, imgDim, hc:img, sz, pos, outMargin
    ET.SubElement(pic, f"{{{HP}}}offset", x="0", y="0")
    ET.SubElement(pic, f"{{{HP}}}orgSz", width=W, height=H)
    ET.SubElement(pic, f"{{{HP}}}curSz", width=W, height=H)
    ET.SubElement(pic, f"{{{HP}}}flip", horizontal="0", vertical="0")
    ET.SubElement(pic, f"{{{HP}}}rotationInfo", {
        "angle": "0", "centerX": W_half, "centerY": H_half, "rotateimage": "1",
    })

    ri = ET.SubElement(pic, f"{{{HP}}}renderingInfo")
    ET.SubElement(ri, f"{{{HC}}}transMatrix",
                  e1="1", e2="0", e3="0", e4="0", e5="1", e6="0")
    ET.SubElement(ri, f"{{{HC}}}scaMatrix",
                  e1="1", e2="0", e3="0", e4="0", e5="1", e6="0")
    ET.SubElement(ri, f"{{{HC}}}rotMatrix",
                  e1="1", e2="-0", e3="0", e4="0", e5="1", e6="0")

    imgRect = ET.SubElement(pic, f"{{{HP}}}imgRect")
    ET.SubElement(imgRect, f"{{{HC}}}pt0", x="0", y="0")
    ET.SubElement(imgRect, f"{{{HC}}}pt1", x=W, y="0")
    ET.SubElement(imgRect, f"{{{HC}}}pt2", x=W, y=H)
    ET.SubElement(imgRect, f"{{{HC}}}pt3", x="0", y=H)

    ET.SubElement(pic, f"{{{HP}}}imgClip",
                  left="0", right=pixW, top="0", bottom=pixH)
    ET.SubElement(pic, f"{{{HP}}}inMargin",
                  left="0", right="0", top="0", bottom="0")
    ET.SubElement(pic, f"{{{HP}}}imgDim", dimwidth=pixW, dimheight=pixH)
    ET.SubElement(pic, f"{{{HC}}}img", {
        "binaryItemIDRef": manifest_id, "bright": "0", "contrast": "0",
        "effect": "REAL_PIC", "alpha": "0",
    })

    # sz, pos, outMargin come AFTER hc:img (Hancom canonical order)
    ET.SubElement(pic, f"{{{HP}}}sz", {
        "width": W, "widthRelTo": "ABSOLUTE",
        "height": H, "heightRelTo": "ABSOLUTE", "protect": "0",
    })
    ET.SubElement(pic, f"{{{HP}}}pos", {
        "treatAsChar": "1", "affectLSpacing": "0", "flowWithText": "0",
        "allowOverlap": "0", "holdAnchorAndSO": "0",
        "vertRelTo": "PARA", "horzRelTo": "COLUMN",
        "vertAlign": "TOP", "horzAlign": "LEFT",
        "vertOffset": "0", "horzOffset": "0",
    })
    ET.SubElement(pic, f"{{{HP}}}outMargin",
                  left="0", right="0", top="0", bottom="0")

    return pic
```

### E. Critical Rules for HWPX `<hp:pic>`

> **All 9 rules must be followed. Violating any one causes broken image rendering.**

| # | Rule | Correct | Wrong |
|---|------|---------|-------|
| 1 | **`<img>` uses `hc:` namespace** | `<hc:img binaryItemIDRef="..."/>` | `<hp:img .../>` |
| 2 | **`<imgRect>` has 4 `<hc:pt>` children** | `<hc:pt0 x="0" y="0"/>` ... `<hc:pt3>` | Inline `x1/y1/x2/y2` attributes |
| 3 | **All required children present** | `offset`, `orgSz`, `curSz`, `flip`, `rotationInfo`, `renderingInfo`, `inMargin` | Missing any of these |
| 4 | **No spurious elements** | Do NOT include `hp:lineShape` | `hp:caption`, `hp:shapeComment`, `hp:lineShape` |
| 5 | **`imgClip` right/bottom = pixel dims** | `right="{pixW}" bottom="{pixH}"` | All zeros |
| 6 | **Hancom canonical element order** | offset, orgSz, ..., hc:img, **then** sz, pos, outMargin | sz/pos first (pre-2026 incorrect order) |
| 7 | **Register in `content.hpf` only** | `<opf:item>` in manifest | `<hh:binDataItems>` in header.xml |
| 8 | **`hp:pos` attributes** | `flowWithText="0"` `horzRelTo="COLUMN"` | `flowWithText="1"` `horzRelTo="PARA"` |
| 9 | **pic INSIDE run, t AFTER pic** | `<hp:run><hp:pic>...</hp:pic><hp:t/></hp:run>` | `<hp:run><hp:t/></hp:run><hp:pic>` |

## Size Calculations

### Dimension Conversion
- **DOCX**: Uses EMUs (English Metric Units)
  - 1 inch = 914,400 EMU
  - 1 mm = 36,000 EMU
  - Formula: `emu = mm * 36000`
- **HWPX**: Uses HWPML units (1/7200 inch)
  - 1 inch = 7,200 units
  - 1 mm ≈ 283.46 units
  - Formula: `hwpml = mm * 283.46` (or `inches * 7200`)
  - Typical A4 text width: ~46,648 units (~165mm)

### Default Dimensions by Image Type (Cell Images)
| image_type | Width (mm) | Height (mm) | DOCX cx (EMU) | DOCX cy (EMU) | HWPX width | HWPX height |
|-----------|-----------|------------|--------------|--------------|-----------|------------|
| photo | 35 | 45 | 1,260,000 | 1,620,000 | 9,922 | 12,757 |
| logo | 50 | 50 | 1,800,000 | 1,800,000 | 14,173 | 14,173 |
| signature | 40 | 15 | 1,440,000 | 540,000 | 11,339 | 4,252 |
| figure (cell) | — | — | — | — | Fit to cell | Fit to cell |

**Cell images**: Use `cellSz` width/height minus margins for aspect-ratio-preserving fit.

### Default Dimensions for Section Content Images
| content_type | HWPX width | HWPX height | Approx mm | Note |
|---|---|---|---|---|
| diagram | 36,000 | 24,000 | 127x85 | ~77% of page width |
| flowchart | 36,000 | 24,000 | 127x85 | ~77% of page width |
| data (charts) | 36,000 | 20,000 | 127x71 | Wide format |
| concept | 28,000 | 28,000 | 99x99 | Square |
| infographic | 36,000 | 24,000 | 127x85 | ~77% of page width |

### Python Code Snippet for DOCX Drawing Element Construction
```python
import xml.etree.ElementTree as ET

def build_drawing_element(rel_id: str, width_emu: int, height_emu: int, pic_id: int, filename: str) -> ET.Element:
    """Build a w:drawing element for image insertion."""
    WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
    A = "http://schemas.openxmlformats.org/drawingml/2006/main"
    PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
    R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

    drawing = ET.Element(f"{{{W}}}drawing")
    inline = ET.SubElement(drawing, f"{{{WP}}}inline",
                           distT="0", distB="0", distL="0", distR="0")
    ET.SubElement(inline, f"{{{WP}}}extent",
                  cx=str(width_emu), cy=str(height_emu))
    ET.SubElement(inline, f"{{{WP}}}docPr",
                  id=str(pic_id), name=f"Picture {pic_id}")

    graphic = ET.SubElement(inline, f"{{{A}}}graphic")
    graphicData = ET.SubElement(graphic, f"{{{A}}}graphicData",
                                uri="http://schemas.openxmlformats.org/drawingml/2006/picture")

    pic = ET.SubElement(graphicData, f"{{{PIC}}}pic")
    nvPicPr = ET.SubElement(pic, f"{{{PIC}}}nvPicPr")
    ET.SubElement(nvPicPr, f"{{{PIC}}}cNvPr", id=str(pic_id), name=filename)
    ET.SubElement(nvPicPr, f"{{{PIC}}}cNvPicPr")

    blipFill = ET.SubElement(pic, f"{{{PIC}}}blipFill")
    ET.SubElement(blipFill, f"{{{A}}}blip", attrib={f"{{{R}}}embed": rel_id})
    stretch = ET.SubElement(blipFill, f"{{{A}}}stretch")
    ET.SubElement(stretch, f"{{{A}}}fillRect")

    spPr = ET.SubElement(pic, f"{{{PIC}}}spPr")
    xfrm = ET.SubElement(spPr, f"{{{A}}}xfrm")
    ET.SubElement(xfrm, f"{{{A}}}off", x="0", y="0")
    ET.SubElement(xfrm, f"{{{A}}}ext", cx=str(width_emu), cy=str(height_emu))
    prstGeom = ET.SubElement(spPr, f"{{{A}}}prstGeom", prst="rect")
    ET.SubElement(prstGeom, f"{{{A}}}avLst")

    return drawing
```
