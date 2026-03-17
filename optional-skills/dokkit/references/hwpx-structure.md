# HWPX XML Structure Reference

## Unpacking an HWPX

```bash
mkdir -p .dokkit/template_work
cd .dokkit/template_work
unzip -o /path/to/template.hwpx
```

## Reading Section XML

```python
import xml.etree.ElementTree as ET

# Parse section file
tree = ET.parse("Contents/section0.xml")
root = tree.getroot()

# HWPX namespaces
ns = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "opf": "http://www.idpf.org/2007/opf",
}

# Find all paragraphs
for p in root.iter("{http://www.hancom.co.kr/hwpml/2011/paragraph}p"):
    texts = []
    for t in p.iter("{http://www.hancom.co.kr/hwpml/2011/paragraph}t"):
        if t.text:
            texts.append(t.text)
    if texts:
        print("".join(texts))
```

## CRITICAL: Preserving Namespace Declarations

Python's `xml.etree.ElementTree` **strips unused namespace declarations** when re-serializing XML. This breaks Hancom/Polaris Office, which requires ALL original namespace declarations on EVERY XML root element, even if no elements use those prefixes.

**This applies to ALL HWPX XML files**, not just `section0.xml`:
- `Contents/section0.xml` — root `<hs:sec>` needs 14+ xmlns
- `Contents/content.hpf` — root `<opf:package>` needs 14+ xmlns
- `Contents/header.xml` — root `<hh:head>` needs 14+ xmlns

**After any ET-based XML modification**, you MUST restore the original namespace declarations:

```python
# After tree.write(), fix the root element:
import re

with open(section_xml_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Capture original namespace declarations BEFORE any ET parsing
ORIGINAL_ROOT_NS = (
    'xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app" '
    'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
    'xmlns:hp10="http://www.hancom.co.kr/hwpml/2016/paragraph" '
    'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
    'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" '
    'xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" '
    'xmlns:hhs="http://www.hancom.co.kr/hwpml/2011/history" '
    'xmlns:hm="http://www.hancom.co.kr/hwpml/2011/master-page" '
    'xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/" '
    'xmlns:ooxmlchart="http://www.hancom.co.kr/hwpml/2016/ooxmlchart" '
    'xmlns:epub="http://www.idpf.org/2007/ops" '
    'xmlns:config="urn:oasis:names:tc:opendocument:xmlns:config:1.0" '
    'xmlns:opf="http://www.idpf.org/2007/opf/"'
)

# Replace stripped root with full original declarations
content = re.sub(
    r'<hs:sec\s+xmlns:[^>]+>',
    f'<hs:sec {ORIGINAL_ROOT_NS}>',
    content, count=1
)

# Also restore XML declaration to original format
content = re.sub(
    r"<\?xml version='1\.0' encoding='UTF-8'\?>",
    '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>',
    content, count=1
)

with open(section_xml_path, 'w', encoding='utf-8') as f:
    f.write(content)
```

**Also remove newlines** that ET inserts between the XML declaration and root element:
```python
content = content.replace('?>\n<', '?><')
```

**Best practice**: Before calling `ET.parse()`, save the original root opening tag. After `tree.write()`, replace the new root tag with the saved original. Apply this to EVERY HWPX XML file you modify (section0.xml, content.hpf, header.xml).

## Repackaging an HWPX

CRITICAL: The `mimetype` file must be first and uncompressed.

```python
import zipfile
import os

def repackage_hwpx(work_dir, output_path):
    """Repackage modified XML files into a valid HWPX."""
    with zipfile.ZipFile(output_path, 'w') as zf:
        # mimetype MUST be first and uncompressed
        mimetype_path = os.path.join(work_dir, "mimetype")
        if os.path.exists(mimetype_path):
            zf.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)

        # Add all other files with compression
        for root, dirs, files in os.walk(work_dir):
            for file in files:
                if file == "mimetype":
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, work_dir)
                zf.write(file_path, arcname, compress_type=zipfile.ZIP_DEFLATED)
```

## BinData and Image Handling

### BinData Directory
The `BinData/` directory (at the archive root) stores embedded binary resources — primarily images. Files are named sequentially: `image1.png`, `image2.jpg`, etc.

### Image Registration — Manifest Only
Images are registered ONLY in `Contents/content.hpf` via `<opf:item>` elements:
```xml
<opf:item id="image1" href="BinData/image1.png" media-type="image/png" isEmbeded="1"/>
```

**Critical**: Do NOT add `<hh:binDataItems>` entries to `header.xml` for images. The `content.hpf` manifest is the sole registration point. No entries are needed in `META-INF/manifest.xml` either.

### Image Elements Use `hc:` Namespace
The `<img>` element inside `<hp:pic>` uses the **core** namespace (`hc:`), not the paragraph namespace (`hp:`):
```xml
<!-- CORRECT -->
<hc:img binaryItemIDRef="image1" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/>

<!-- WRONG — will not render -->
<hp:img binaryItemIDRef="image1" .../>
```

See the `dokkit-image-sourcing` skill for the complete `<hp:pic>` element structure with all required children.

## Critical Rules for HWPX Surgery

1. **`mimetype` must be first in ZIP** — stored uncompressed
2. **Preserve `hp:rPr` elements** — character formatting
3. **Don't modify `hp:cellSpan`** — cell merging must remain intact
4. **Keep `hp:cellAddr` — and ensure `rowAddr` = row index** — Each `<hp:tc>` has `<hp:cellAddr colAddr="C" rowAddr="R"/>` where `R` MUST equal the 0-based index of the parent `<hp:tr>` within the `<hp:tbl>`. If two rows share the same `rowAddr`, Polaris Office **silently hides** the duplicate — the table renders with missing data and no error. After any row insertion, deletion, or reordering, re-index ALL `rowAddr` values and update `<hp:tbl rowCnt="N">`.
5. **Preserve paragraph properties** — `hp:pPr` controls alignment, spacing
6. **Korean font references** — don't change `hangulFont`, `latinFont` attributes
7. **Section boundaries** — each section file is independent
