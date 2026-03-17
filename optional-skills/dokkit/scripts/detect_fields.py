#!/usr/bin/env python3
"""Detect fillable fields in a DOCX document.xml file.

Usage:
    python detect_fields.py <path-to-document.xml>

Output:
    JSON array of detected fields to stdout.
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

# Keywords that indicate image fields (Korean and English)
IMAGE_KEYWORDS_KO = ["사진", "증명사진", "여권사진", "로고", "서명", "날인", "도장", "직인"]
IMAGE_KEYWORDS_EN = ["photo", "picture", "logo", "signature", "stamp", "seal", "image", "portrait"]
IMAGE_KEYWORDS = IMAGE_KEYWORDS_KO + IMAGE_KEYWORDS_EN

# Map keywords to image_type classifier
IMAGE_TYPE_MAP = {
    "사진": "photo", "증명사진": "photo", "여권사진": "photo",
    "photo": "photo", "picture": "photo", "portrait": "photo", "image": "photo",
    "로고": "logo", "logo": "logo",
    "서명": "signature", "날인": "signature", "stamp": "signature", "seal": "signature",
    "도장": "signature", "직인": "signature",
}


def get_text(elem) -> str:
    """Extract all text from an element and its children."""
    texts = []
    for t in elem.iter("{%s}t" % NS["w"]):
        if t.text:
            texts.append(t.text)
    return "".join(texts)


def _classify_image_type(text: str) -> str:
    """Classify image type from text. Returns photo/logo/signature/figure."""
    lower = text.lower().strip()
    for keyword, img_type in IMAGE_TYPE_MAP.items():
        if keyword in lower:
            return img_type
    return "figure"


def _is_image_keyword(text: str) -> bool:
    """Check if text contains an image-related keyword."""
    lower = text.lower().strip()
    return any(kw in lower for kw in IMAGE_KEYWORDS)


def detect_placeholder_text(root) -> list[dict]:
    """Find {{placeholder}} and <<placeholder>> patterns (excluding image keywords)."""
    fields = []
    pattern = re.compile(r"\{\{([^}]+)\}\}|<<([^>]+)>>|\[([^\]]+)\]")

    for i, p in enumerate(root.iter("{%s}p" % NS["w"])):
        text = get_text(p)
        for match in pattern.finditer(text):
            label = match.group(1) or match.group(2) or match.group(3)
            # Skip image keywords — handled by detect_image_fields
            if _is_image_keyword(label):
                continue
            fields.append({
                "label": label.strip(),
                "field_type": "placeholder_text",
                "pattern": match.group(0),
                "xml_path": f"p[{i}]",
            })
    return fields


def detect_empty_table_cells(root) -> list[dict]:
    """Find empty table cells adjacent to label cells."""
    fields = []

    for ti, tbl in enumerate(root.iter("{%s}tbl" % NS["w"])):
        for ri, tr in enumerate(tbl.iter("{%s}tr" % NS["w"])):
            cells = list(tr.iter("{%s}tc" % NS["w"]))
            for ci in range(len(cells) - 1):
                label_text = get_text(cells[ci]).strip()
                next_text = get_text(cells[ci + 1]).strip()

                if label_text and not next_text and len(label_text) < 50:
                    # Skip image keywords — handled by detect_image_fields
                    if _is_image_keyword(label_text):
                        continue
                    fields.append({
                        "label": label_text,
                        "field_type": "empty_cell",
                        "pattern": "(empty cell)",
                        "xml_path": f"tbl[{ti}]/tr[{ri}]/tc[{ci + 1}]",
                    })
    return fields


def detect_underline_fields(root) -> list[dict]:
    """Find underline-only runs (blank line placeholders)."""
    fields = []

    for i, r in enumerate(root.iter("{%s}r" % NS["w"])):
        rPr = r.find("{%s}rPr" % NS["w"])
        if rPr is None:
            continue
        u = rPr.find("{%s}u" % NS["w"])
        if u is None:
            continue

        t = r.find("{%s}t" % NS["w"])
        if t is not None and t.text:
            text = t.text.strip()
            if not text or all(c in " _" for c in text):
                # Find preceding text for label
                parent_p = None
                for p in root.iter("{%s}p" % NS["w"]):
                    if r in list(p):
                        parent_p = p
                        break

                label = "underline_field"
                if parent_p is not None:
                    full_text = get_text(parent_p)
                    # Try to extract label from surrounding text
                    clean = full_text.replace(t.text, "").strip()
                    if clean:
                        label = clean

                fields.append({
                    "label": label,
                    "field_type": "underline",
                    "pattern": "(underline)",
                    "xml_path": f"r[{i}]",
                })
    return fields


def detect_content_controls(root) -> list[dict]:
    """Find structured document tags (content controls)."""
    fields = []

    for i, sdt in enumerate(root.iter("{%s}sdt" % NS["w"])):
        sdtPr = sdt.find("{%s}sdtPr" % NS["w"])
        if sdtPr is None:
            continue

        # Get alias or tag
        alias = sdtPr.find("{%s}alias" % NS["w"])
        tag = sdtPr.find("{%s}tag" % NS["w"])

        label = "unknown"
        if alias is not None:
            label = alias.get("{%s}val" % NS["w"], "unknown")
        elif tag is not None:
            label = tag.get("{%s}val" % NS["w"], "unknown")

        fields.append({
            "label": label,
            "field_type": "form_control",
            "pattern": "(content control)",
            "xml_path": f"sdt[{i}]",
        })
    return fields


def detect_image_fields(root) -> list[dict]:
    """Detect image placeholders in a DOCX document.

    Detects:
    - Existing <w:drawing> elements in table cells (pre-positioned image slots)
    - Image placeholder text: {{photo}}, {{사진}}, <<signature>>, etc.
    - Empty cells adjacent to image-keyword labels
    """
    fields = []
    placeholder_pattern = re.compile(
        r"\{\{([^}]+)\}\}|<<([^>]+)>>|\[([^\]]+)\]"
    )

    # 1. Detect image placeholder text ({{photo}}, <<signature>>, etc.)
    for i, p in enumerate(root.iter("{%s}p" % NS["w"])):
        text = get_text(p)
        for match in placeholder_pattern.finditer(text):
            label = match.group(1) or match.group(2) or match.group(3)
            if _is_image_keyword(label):
                fields.append({
                    "label": label.strip(),
                    "field_type": "image",
                    "image_type": _classify_image_type(label),
                    "pattern": match.group(0),
                    "xml_path": f"p[{i}]",
                })

    # 2. Detect existing <w:drawing> placeholders in table cells
    for ti, tbl in enumerate(root.iter("{%s}tbl" % NS["w"])):
        for ri, tr in enumerate(tbl.iter("{%s}tr" % NS["w"])):
            cells = list(tr.iter("{%s}tc" % NS["w"]))
            for ci, cell in enumerate(cells):
                drawings = list(cell.iter("{%s}drawing" % NS["w"]))
                if drawings:
                    # Cell has a drawing — check if adjacent cell has image-keyword label
                    label_text = ""
                    if ci > 0:
                        label_text = get_text(cells[ci - 1]).strip()
                    if not _is_image_keyword(label_text) and ci + 1 < len(cells):
                        label_text = get_text(cells[ci + 1]).strip()
                    if not _is_image_keyword(label_text):
                        label_text = "image_placeholder"

                    fields.append({
                        "label": label_text,
                        "field_type": "image",
                        "image_type": _classify_image_type(label_text),
                        "pattern": "(existing drawing)",
                        "xml_path": f"tbl[{ti}]/tr[{ri}]/tc[{ci}]",
                    })

    # 3. Detect empty cells adjacent to image-keyword labels
    for ti, tbl in enumerate(root.iter("{%s}tbl" % NS["w"])):
        for ri, tr in enumerate(tbl.iter("{%s}tr" % NS["w"])):
            cells = list(tr.iter("{%s}tc" % NS["w"]))
            for ci in range(len(cells) - 1):
                label_text = get_text(cells[ci]).strip()
                next_text = get_text(cells[ci + 1]).strip()

                if _is_image_keyword(label_text) and not next_text:
                    # Check the empty cell doesn't already have a drawing
                    has_drawing = bool(list(cells[ci + 1].iter("{%s}drawing" % NS["w"])))
                    if not has_drawing:
                        fields.append({
                            "label": label_text,
                            "field_type": "image",
                            "image_type": _classify_image_type(label_text),
                            "pattern": "(empty cell, image label)",
                            "xml_path": f"tbl[{ti}]/tr[{ri}]/tc[{ci + 1}]",
                        })

    return fields


def detect_instruction_text(root) -> list[dict]:
    """Find instruction text patterns like (enter name here)."""
    fields = []
    pattern = re.compile(
        r"\(.*?(?:enter|type|input|write|fill|입력|기재|작성).*?\)",
        re.IGNORECASE
    )

    for i, p in enumerate(root.iter("{%s}p" % NS["w"])):
        text = get_text(p)
        for match in pattern.finditer(text):
            fields.append({
                "label": match.group(0).strip("()"),
                "field_type": "instruction_text",
                "pattern": match.group(0),
                "xml_path": f"p[{i}]",
            })
    return fields


def main():
    if len(sys.argv) != 2:
        print("Usage: python detect_fields.py <document.xml>", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(json.dumps({"error": f"File not found: {path}"}))
        sys.exit(1)

    tree = ET.parse(path)
    root = tree.getroot()

    all_fields = []
    all_fields.extend(detect_placeholder_text(root))
    all_fields.extend(detect_empty_table_cells(root))
    all_fields.extend(detect_underline_fields(root))
    all_fields.extend(detect_content_controls(root))
    all_fields.extend(detect_instruction_text(root))
    all_fields.extend(detect_image_fields(root))

    # Assign IDs
    for i, field in enumerate(all_fields):
        field["id"] = f"field_{i + 1:03d}"

    print(json.dumps(all_fields, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
