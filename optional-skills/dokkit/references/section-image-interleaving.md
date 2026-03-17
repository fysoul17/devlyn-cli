# Section Content Image Interleaving

Algorithm and code patterns for inserting AI-generated images within `section_content` fields, interleaved between text paragraphs.

## Overview

When a `section_content` field has `image_opportunities` in analysis.json, the filler must:
1. Resolve each opportunity's anchor text to a specific paragraph in the XML
2. Build an image paragraph (`<hp:p>` or `<w:p>`) containing the image element
3. Insert the image paragraph **after** the anchor paragraph
4. Register the image in the document manifest

## Algorithm: `fill_section_content_with_images()`

```python
def fill_section_content_with_images(
    section_root,       # The section XML root element
    content_elements,   # List of XML elements in the section_content range
    mapped_value,       # The text content (markdown string)
    image_opportunities,# List of image opportunity dicts from analysis.json
    format_context,     # Dict with charPrIDs, header_path, etc.
    template_type,      # "hwpx" or "docx"
    work_dir,           # Path to template_work directory
):
    """Fill section content with text AND interleaved images.

    Strategy:
    1. First, fill the section content with formatted text (existing logic)
    2. Then, for each sourced image opportunity, find the anchor paragraph
       and insert an image paragraph after it
    """
    # Step 1: Fill text content using existing fill_section_content() logic
    # (This creates all the text paragraphs with markdown formatting)
    fill_section_content(section_root, content_elements, mapped_value, format_context, template_type)

    # Step 2: Insert images at anchor points
    sourced = [op for op in image_opportunities if op.get("status") == "sourced" and op.get("image_file")]

    for opportunity in sourced:
        anchor_text = opportunity["insertion_point"]["anchor_text"]
        image_file = opportunity["image_file"]
        dims = opportunity.get("dimensions", {})

        # Find the anchor paragraph
        anchor_p = find_anchor_paragraph(section_root, content_elements, anchor_text, template_type)
        if anchor_p is None:
            print(f"WARNING: Anchor text not found for {opportunity['opportunity_id']}, skipping image")
            opportunity["status"] = "skipped"
            continue

        # Build image paragraph
        if template_type == "hwpx":
            img_p = build_hwpx_image_paragraph(
                image_file, dims, format_context, work_dir
            )
        else:
            img_p = build_docx_image_paragraph(
                image_file, dims, format_context, work_dir
            )

        # Insert after anchor paragraph
        insert_after_element(section_root, anchor_p, img_p)
        opportunity["status"] = "inserted"
```

## Anchor Text Resolution

The anchor text is a distinctive Korean phrase from the paragraph where the image should be inserted **after**.

```python
def find_anchor_paragraph(section_root, content_elements, anchor_text, template_type):
    """Find the paragraph element containing the anchor text.

    Search strategy:
    1. Exact substring match in paragraph text
    2. Normalized match (strip whitespace differences)
    3. Partial match (first 20 chars of anchor)

    Returns the <hp:p> or <w:p> element, or None if not found.
    """
    ns_t = "{http://www.hancom.co.kr/hwpml/2011/paragraph}t" if template_type == "hwpx" else "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
    ns_p = "{http://www.hancom.co.kr/hwpml/2011/paragraph}p" if template_type == "hwpx" else "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"

    # Collect all paragraphs within the content range
    paragraphs = []
    for elem in content_elements:
        if elem.tag == ns_p:
            paragraphs.append(elem)
        for child_p in elem.iter(ns_p):
            if child_p not in paragraphs:
                paragraphs.append(child_p)

    # Strategy 1: Exact substring match
    for p in paragraphs:
        text = "".join(t.text or "" for t in p.iter(ns_t))
        if anchor_text in text:
            return p

    # Strategy 2: Normalized match (collapse whitespace)
    import re
    normalized_anchor = re.sub(r'\s+', ' ', anchor_text.strip())
    for p in paragraphs:
        text = "".join(t.text or "" for t in p.iter(ns_t))
        normalized_text = re.sub(r'\s+', ' ', text.strip())
        if normalized_anchor in normalized_text:
            return p

    # Strategy 3: Partial match (first 20 chars)
    partial = anchor_text[:20]
    for p in paragraphs:
        text = "".join(t.text or "" for t in p.iter(ns_t))
        if partial in text:
            return p

    return None  # Not found — caller should skip with warning
```

## Image Paragraph Construction

### HWPX: `<hp:p>` with `<hp:pic>`

```python
def find_center_parapr(header_path):
    """Find first center-aligned paraPr from header.xml for image paragraphs."""
    HH = "http://www.hancom.co.kr/hwpml/2011/head"
    tree = ET.parse(header_path)
    for pp in tree.getroot().iter(f"{{{HH}}}paraPr"):
        align = pp.find(f"{{{HH}}}align")
        if align is not None and align.get("horizontal") == "CENTER":
            return pp.get("id")
    return "0"  # fallback to default


def build_hwpx_image_paragraph(image_file, dims, format_context, work_dir):
    """Build an <hp:p> element containing an <hp:pic> for inline image display.

    The paragraph contains:
    - A <hp:run> with an empty <hp:t> (required for valid paragraph structure)
    - A <hp:pic> element (the actual image)
    - Center-aligned paraPrIDRef from header.xml
    """
    HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"

    # Use dimensions from opportunity, with defaults (~77% of A4 page width)
    width_hwpml = dims.get("width_hwpml", 36000)   # ~127mm default
    height_hwpml = dims.get("height_hwpml", 24000)  # ~85mm default

    # Override small legacy defaults (15000 = ~53mm, too small for page)
    if width_hwpml <= 16000:
        width_hwpml = 36000
    if height_hwpml <= 12000:
        height_hwpml = int(width_hwpml * 0.667)

    # Copy image to BinData/ and register in manifest
    manifest_id, bin_path = register_image_in_manifest(image_file, work_dir)

    # Get next sequential ID and zOrder from section XML
    seq_id = format_context["next_seq_id"]
    z_order = format_context["next_z_order"]
    format_context["next_seq_id"] += 1
    format_context["next_z_order"] += 1

    # Find center-aligned paraPrIDRef from header.xml
    center_parapr_id = format_context.get("center_parapr_id")
    if center_parapr_id is None:
        center_parapr_id = find_center_parapr(
            os.path.join(work_dir, "Contents", "header.xml")
        )
        format_context["center_parapr_id"] = center_parapr_id

    # Build the paragraph with center alignment
    p = ET.Element(f"{{{HP}}}p")
    p.set("paraPrIDRef", str(center_parapr_id))
    p.set("styleIDRef", "0")
    p.set("pageBreak", "0")
    p.set("columnBreak", "0")
    p.set("merged", "0")

    # Hancom structure: <hp:run><hp:pic>...</hp:pic><hp:t/></hp:run>
    # pic goes INSIDE run, t AFTER pic (verified against real Hancom Office output)
    run = ET.SubElement(p, f"{{{HP}}}run")
    run.set("charPrIDRef", str(format_context.get("normal_charpr_id", "0")))

    # Build <hp:pic> element and append INSIDE the run
    pic = build_hwpx_pic_element(
        manifest_id=manifest_id,
        image_path=bin_path,
        width_hwpml=width_hwpml,
        height_hwpml=height_hwpml,
        seq_id=seq_id,
        z_order=z_order,
    )
    run.append(pic)

    # Empty <hp:t/> goes AFTER <hp:pic> inside the run
    ET.SubElement(run, f"{{{HP}}}t")

    return p
```

### DOCX: `<w:p>` with `<w:drawing>`

```python
def build_docx_image_paragraph(image_file, dims, format_context, work_dir):
    """Build a <w:p> element containing a <w:drawing> for inline image display."""
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

    width_emu = dims.get("width_emu", 5400000)    # 150mm default
    height_emu = dims.get("height_emu", 3600000)   # 100mm default

    # Copy image to word/media/ and register relationship
    rel_id, media_path = register_image_in_docx(image_file, work_dir)
    pic_id = format_context["next_pic_id"]
    format_context["next_pic_id"] += 1
    filename = os.path.basename(media_path)

    # Build the paragraph
    p = ET.Element(f"{{{W}}}p")

    # Center alignment for the image paragraph
    pPr = ET.SubElement(p, f"{{{W}}}pPr")
    jc = ET.SubElement(pPr, f"{{{W}}}jc")
    jc.set(f"{{{W}}}val", "center")

    # Build the run with drawing
    r = ET.SubElement(p, f"{{{W}}}r")
    # Use build_drawing_element() from dokkit-image-sourcing skill
    drawing = build_drawing_element(rel_id, width_emu, height_emu, pic_id, filename)
    r.append(drawing)

    return p
```

## Element Insertion

```python
def insert_after_element(root, anchor_elem, new_elem):
    """Insert new_elem immediately after anchor_elem in the parent's children.

    Handles both direct children and nested elements by building a parent map.
    """
    parent_map = {c: p for p in root.iter() for c in p}
    parent = parent_map.get(anchor_elem)
    if parent is None:
        return False

    children = list(parent)
    idx = children.index(anchor_elem)
    parent.insert(idx + 1, new_elem)
    return True
```

## Image Registration (same rules as cell-level images)

### HWPX Registration
```python
def register_image_in_manifest(image_file, work_dir):
    """Copy image to BinData/ and register in content.hpf manifest.

    Returns (manifest_id, bin_path).
    Same rules as cell-level image registration:
    - Register in content.hpf ONLY
    - Do NOT add to header.xml binDataItems
    """
    import shutil
    import os

    # Find next available image number
    bindata_dir = os.path.join(work_dir, "BinData")
    os.makedirs(bindata_dir, exist_ok=True)
    existing = [f for f in os.listdir(bindata_dir) if f.startswith("image")]
    next_n = len(existing) + 1
    ext = os.path.splitext(image_file)[1]
    filename = f"image{next_n}{ext}"
    bin_path = os.path.join(bindata_dir, filename)
    shutil.copy2(image_file, bin_path)

    # Register in content.hpf
    manifest_id = f"image{next_n}"
    content_hpf = os.path.join(work_dir, "Contents", "content.hpf")
    # Add <opf:item id="imageN" href="BinData/imageN.ext" media-type="image/png" isEmbeded="1"/>
    # (Filler agent performs the actual XML modification)

    return manifest_id, bin_path
```

### DOCX Registration
```python
def register_image_in_docx(image_file, work_dir):
    """Copy image to word/media/ and register in relationships and Content_Types.

    Returns (rel_id, media_path).
    Same rules as cell-level image registration:
    - Add relationship in word/_rels/document.xml.rels
    - Add Content_Types entry if extension not registered
    """
    import shutil
    import os

    media_dir = os.path.join(work_dir, "word", "media")
    os.makedirs(media_dir, exist_ok=True)
    existing = [f for f in os.listdir(media_dir) if f.startswith("image")]
    next_n = len(existing) + 1
    ext = os.path.splitext(image_file)[1]
    filename = f"image{next_n}{ext}"
    media_path = os.path.join(media_dir, filename)
    shutil.copy2(image_file, media_path)

    # Generate next relationship ID
    rel_id = f"rId{next_n + 10}"  # offset to avoid conflicts
    # (Filler agent adds the actual relationship XML and Content_Types entry)

    return rel_id, media_path
```

## Edge Cases

### Anchor text not found
- **Action**: Skip the image opportunity, set `status: "skipped"`, log a warning
- **Cause**: Text may have been modified during markdown rendering, or anchor was not distinctive enough
- **Mitigation**: Analyzer should choose anchor text that is unique within the field

### Image generation failure
- **Action**: The image_file will be null and status remains "pending" (fill-doc sets to "skipped" on failure)
- **Filler behavior**: Skip opportunities where `status != "sourced"`, proceed with text-only fill
- **No fallback**: Do not insert placeholder images or broken references

### Multiple images in same paragraph area
- **Rule**: Min 150 chars between image opportunities (enforced by analyzer)
- **If violated**: Insert images in order; later images shift down naturally

### Content too short after formatting
- **Rule**: If the filled section has fewer paragraphs than expected (e.g., due to markdown rendering differences), skip any opportunities whose anchor text cannot be found
- **Never force**: Do not insert images at approximate positions if anchor resolution fails

## Dimension Defaults for Section Content Images

HWPML units are 1/7200 inch (NOT hundredths of mm). ~77% of A4 text width = 36,000 units.

| content_type | HWPML width | HWPML height | Approx mm | EMU cx | EMU cy |
|---|---|---|---|---|---|
| diagram | 36,000 | 24,000 | 127x85 | 4,572,000 | 3,048,000 |
| flowchart | 36,000 | 24,000 | 127x85 | 4,572,000 | 3,048,000 |
| data | 36,000 | 20,000 | 127x71 | 4,572,000 | 2,540,000 |
| concept | 28,000 | 28,000 | 99x99 | 3,556,000 | 3,556,000 |
| infographic | 36,000 | 24,000 | 127x85 | 4,572,000 | 3,048,000 |
