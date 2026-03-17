#!/usr/bin/env python3
"""Parse HWPX files into Dokkit's dual-file format (Markdown + JSON sidecar).

HWPX is a ZIP archive containing XML files following the OWPML standard.
Structure: Contents/section0.xml, Contents/section1.xml, etc.

Usage:
    python parse_hwpx.py <input.hwpx>

Output:
    JSON to stdout with 'content_md' and 'metadata' fields.
"""

import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path


# HWPX XML namespaces
NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
}


def extract_text_from_element(elem) -> str:
    """Recursively extract text from an XML element and its children."""
    texts = []
    # Check for direct text
    if elem.text:
        texts.append(elem.text)

    for child in elem:
        # Look for text runs
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag in ("t", "text"):
            if child.text:
                texts.append(child.text)
        elif tag == "run":
            texts.append(extract_text_from_element(child))
        elif tag == "lineseg":
            texts.append(extract_text_from_element(child))
        else:
            texts.append(extract_text_from_element(child))

        if child.tail:
            texts.append(child.tail)

    return "".join(texts)


def parse_table(table_elem) -> list[list[str]]:
    """Parse a table element into a 2D list of cell values."""
    rows = []
    for row_elem in table_elem:
        tag = row_elem.tag.split("}")[-1] if "}" in row_elem.tag else row_elem.tag
        if tag != "tr":
            continue
        cells = []
        for cell_elem in row_elem:
            cell_tag = cell_elem.tag.split("}")[-1] if "}" in cell_elem.tag else cell_elem.tag
            if cell_tag != "tc":
                continue
            cell_text = extract_text_from_element(cell_elem).strip()
            cells.append(cell_text)
        if cells:
            rows.append(cells)
    return rows


def parse_section(xml_content: str, section_name: str) -> tuple[str, dict]:
    """Parse a single section XML and return markdown content + key-value pairs."""
    root = ET.fromstring(xml_content)
    content_parts = []
    key_value_pairs = {}

    content_parts.append(f"## {section_name}\n")

    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

        if tag == "p":
            text = extract_text_from_element(elem).strip()
            if text:
                content_parts.append(text)

        elif tag == "tbl":
            rows = parse_table(elem)
            if rows:
                # Convert to markdown table
                if len(rows) > 0:
                    max_cols = max(len(r) for r in rows)
                    # Pad rows to same length
                    for r in rows:
                        while len(r) < max_cols:
                            r.append("")

                    content_parts.append("")
                    content_parts.append("| " + " | ".join(rows[0]) + " |")
                    content_parts.append("| " + " | ".join(["---"] * max_cols) + " |")
                    for row in rows[1:]:
                        content_parts.append("| " + " | ".join(row) + " |")
                    content_parts.append("")

                    # Extract key-value pairs from 2-column tables
                    for row in rows:
                        if len(row) >= 2 and row[0] and row[1]:
                            label = row[0].strip()
                            value = row[1].strip()
                            if len(label) < 50:
                                key_value_pairs[label] = value

    return "\n".join(content_parts), key_value_pairs


def parse_hwpx(file_path: str) -> dict:
    """Parse an HWPX file and return content + metadata."""
    path = Path(file_path)

    if not zipfile.is_zipfile(path):
        return {"error": f"Not a valid HWPX (ZIP) file: {path}"}

    all_content = []
    all_kvp = {}
    sections = []

    with zipfile.ZipFile(path, "r") as zf:
        # Find section files
        section_files = sorted([
            f for f in zf.namelist()
            if f.startswith("Contents/section") and f.endswith(".xml")
        ])

        if not section_files:
            # Try alternate paths
            section_files = sorted([
                f for f in zf.namelist()
                if "section" in f.lower() and f.endswith(".xml")
            ])

        for i, section_file in enumerate(section_files):
            section_name = f"Section {i + 1}"
            sections.append(section_name)

            xml_content = zf.read(section_file).decode("utf-8")
            md_content, kvp = parse_section(xml_content, section_name)
            all_content.append(md_content)
            all_kvp.update(kvp)

    content_md = f"# {path.stem}\n\n" + "\n\n".join(all_content)

    return {
        "content_md": content_md,
        "metadata": {
            "file_name": path.name,
            "file_type": "hwpx",
            "parse_date": datetime.now().isoformat(),
            "key_value_pairs": all_kvp,
            "sections": sections,
            "section_count": len(sections),
        }
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: python parse_hwpx.py <input.hwpx>", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]
    if not Path(file_path).exists():
        print(json.dumps({"error": f"File not found: {file_path}"}))
        sys.exit(1)

    result = parse_hwpx(file_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
