#!/usr/bin/env python3
"""Detect fillable fields in an HWPX section XML file.

Usage:
    python detect_fields_hwpx.py <path-to-section.xml>

Output:
    JSON array of detected fields to stdout.
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/common",
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
    for t in elem.iter("{%s}t" % NS["hp"]):
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


def detect_empty_table_cells(root) -> list[dict]:
    """Find empty table cells adjacent to label cells in HWPX tables (excluding image keywords)."""
    fields = []

    for ti, tbl in enumerate(root.iter("{%s}tbl" % NS["hp"])):
        for ri, tr in enumerate(tbl.iter("{%s}tr" % NS["hp"])):
            cells = list(tr.iter("{%s}tc" % NS["hp"]))
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


def detect_instruction_text(root) -> list[dict]:
    """Find Korean instruction text patterns."""
    fields = []
    pattern = re.compile(
        r"\(.*?(?:입력|기재|작성|enter|type|fill).*?\)",
        re.IGNORECASE
    )

    for i, p in enumerate(root.iter("{%s}p" % NS["hp"])):
        text = get_text(p)
        for match in pattern.finditer(text):
            fields.append({
                "label": match.group(0).strip("()"),
                "field_type": "instruction_text",
                "pattern": match.group(0),
                "xml_path": f"p[{i}]",
            })
    return fields


def detect_placeholder_text(root) -> list[dict]:
    """Find {{placeholder}} patterns in HWPX (excluding image keywords)."""
    fields = []
    pattern = re.compile(r"\{\{([^}]+)\}\}|<<([^>]+)>>")

    for i, p in enumerate(root.iter("{%s}p" % NS["hp"])):
        text = get_text(p)
        for match in pattern.finditer(text):
            label = match.group(1) or match.group(2)
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


def detect_image_fields(root) -> list[dict]:
    """Detect image placeholders in an HWPX section XML.

    Detects:
    - Existing <hp:pic> elements in table cells (pre-positioned image slots)
    - Image placeholder text: {{photo}}, {{사진}}, <<signature>>, etc.
    - Empty cells adjacent to image-keyword labels
    """
    fields = []
    placeholder_pattern = re.compile(r"\{\{([^}]+)\}\}|<<([^>]+)>>")

    # 1. Detect image placeholder text
    for i, p in enumerate(root.iter("{%s}p" % NS["hp"])):
        text = get_text(p)
        for match in placeholder_pattern.finditer(text):
            label = match.group(1) or match.group(2)
            if _is_image_keyword(label):
                fields.append({
                    "label": label.strip(),
                    "field_type": "image",
                    "image_type": _classify_image_type(label),
                    "pattern": match.group(0),
                    "xml_path": f"p[{i}]",
                })

    # 2. Detect existing <hp:pic> elements in table cells
    for ti, tbl in enumerate(root.iter("{%s}tbl" % NS["hp"])):
        for ri, tr in enumerate(tbl.iter("{%s}tr" % NS["hp"])):
            cells = list(tr.iter("{%s}tc" % NS["hp"]))
            for ci, cell in enumerate(cells):
                pics = list(cell.iter("{%s}pic" % NS["hp"]))
                if pics:
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
                        "pattern": "(existing pic)",
                        "xml_path": f"tbl[{ti}]/tr[{ri}]/tc[{ci}]",
                    })

    # 3. Detect empty cells adjacent to image-keyword labels
    for ti, tbl in enumerate(root.iter("{%s}tbl" % NS["hp"])):
        for ri, tr in enumerate(tbl.iter("{%s}tr" % NS["hp"])):
            cells = list(tr.iter("{%s}tc" % NS["hp"]))
            for ci in range(len(cells) - 1):
                label_text = get_text(cells[ci]).strip()
                next_text = get_text(cells[ci + 1]).strip()

                if _is_image_keyword(label_text) and not next_text:
                    has_pic = bool(list(cells[ci + 1].iter("{%s}pic" % NS["hp"])))
                    if not has_pic:
                        fields.append({
                            "label": label_text,
                            "field_type": "image",
                            "image_type": _classify_image_type(label_text),
                            "pattern": "(empty cell, image label)",
                            "xml_path": f"tbl[{ti}]/tr[{ri}]/tc[{ci + 1}]",
                        })

    return fields


def _build_nested_tip_set(root) -> set:
    """Build set of table element IDs that are nested inside subList elements."""
    nested = set()
    for tbl in root.iter("{%s}tbl" % NS["hp"]):
        for sub_list in tbl.iter("{%s}subList" % NS["hp"]):
            for nested_tbl in sub_list.iter("{%s}tbl" % NS["hp"]):
                nested.add(id(nested_tbl))
    return nested


def detect_tip_boxes(root) -> list[dict]:
    """Detect writing tip boxes (작성 팁) — 1×1 tables with ※ guidance text."""
    fields = []
    tip_pattern = re.compile(r"^※|작성\s?팁|작성\s?요령")
    nested_ids = _build_nested_tip_set(root)

    for ti, tbl in enumerate(root.iter("{%s}tbl" % NS["hp"])):
        if tbl.get("rowCnt", "") != "1" or tbl.get("colCnt", "") != "1":
            continue

        text = get_text(tbl).strip()
        if not text or not tip_pattern.search(text):
            continue

        container = "nested" if id(tbl) in nested_ids else "standalone"
        fields.append({
            "label": text[:60] + ("..." if len(text) > 60 else ""),
            "field_type": "tip_box",
            "action": "delete",
            "container": container,
            "pattern": "(tip box: 1×1 table with ※ text)",
            "xml_path": f"tbl[{ti}]",
        })

    return fields


def detect_date_fields(root) -> list[dict]:
    """Find date component cells (cells before 년/월/일 markers)."""
    fields = []

    for ti, tbl in enumerate(root.iter("{%s}tbl" % NS["hp"])):
        for ri, tr in enumerate(tbl.iter("{%s}tr" % NS["hp"])):
            cells = list(tr.iter("{%s}tc" % NS["hp"]))
            for ci, cell in enumerate(cells):
                text = get_text(cell).strip()
                if text in ("년", "월", "일") and ci > 0:
                    prev_text = get_text(cells[ci - 1]).strip()
                    if not prev_text:
                        date_part = {"년": "year", "월": "month", "일": "day"}[text]
                        fields.append({
                            "label": date_part,
                            "field_type": "empty_cell",
                            "pattern": f"(date: {date_part})",
                            "xml_path": f"tbl[{ti}]/tr[{ri}]/tc[{ci - 1}]",
                        })
    return fields


def main():
    if len(sys.argv) != 2:
        print("Usage: python detect_fields_hwpx.py <section.xml>", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(json.dumps({"error": f"File not found: {path}"}))
        sys.exit(1)

    tree = ET.parse(path)
    root = tree.getroot()

    all_fields = []
    all_fields.extend(detect_empty_table_cells(root))
    all_fields.extend(detect_instruction_text(root))
    all_fields.extend(detect_placeholder_text(root))
    all_fields.extend(detect_date_fields(root))
    all_fields.extend(detect_image_fields(root))
    all_fields.extend(detect_tip_boxes(root))

    # Assign IDs
    for i, field in enumerate(all_fields):
        field["id"] = f"field_{i + 1:03d}"

    print(json.dumps(all_fields, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
