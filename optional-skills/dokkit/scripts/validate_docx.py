#!/usr/bin/env python3
"""Validate a modified DOCX working directory for XML well-formedness.

Usage:
    python validate_docx.py <work_dir>

Checks:
- All XML files are well-formed
- Required files exist ([Content_Types].xml, word/document.xml)
- No broken element nesting
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


REQUIRED_FILES = [
    "[Content_Types].xml",
    "word/document.xml",
]

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".gif", ".webp"}


def validate_xml_file(path: Path) -> list[str]:
    """Check if an XML file is well-formed."""
    errors = []
    try:
        ET.parse(path)
    except ET.ParseError as e:
        errors.append(f"{path}: XML parse error: {e}")
    return errors


def validate_image_relationships(work_dir: Path) -> list[str]:
    """Verify that image media files, relationships, and Content_Types are consistent."""
    errors = []

    # 1. Collect actual image files in word/media/
    media_dir = work_dir / "word" / "media"
    media_images = set()
    if media_dir.is_dir():
        for f in media_dir.iterdir():
            if f.suffix.lower() in IMAGE_EXTENSIONS:
                media_images.add(f.name)

    if not media_images:
        return errors  # No images, nothing to validate

    # 2. Parse relationships to find image references
    rels_path = work_dir / "word" / "_rels" / "document.xml.rels"
    rel_targets = set()
    if rels_path.exists():
        try:
            tree = ET.parse(rels_path)
            root = tree.getroot()
            ns = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
            image_type = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
            for rel in root.iter("{%s}Relationship" % ns["r"]):
                if rel.get("Type") == image_type:
                    target = rel.get("Target", "")
                    # Target is like "media/image1.png"
                    if target.startswith("media/"):
                        rel_targets.add(target[len("media/"):])
        except ET.ParseError:
            pass  # XML error already caught by validate_xml_file

    # 3. Check media files have corresponding relationships
    for img in media_images:
        if img not in rel_targets:
            errors.append(f"Image file word/media/{img} has no relationship entry in document.xml.rels")

    # 4. Check relationships point to existing files
    for target in rel_targets:
        if target not in media_images:
            errors.append(f"Relationship references media/{target} but file does not exist in word/media/")

    # 5. Check Content_Types has entries for image extensions used
    ct_path = work_dir / "[Content_Types].xml"
    if ct_path.exists():
        try:
            ct_tree = ET.parse(ct_path)
            ct_root = ct_tree.getroot()
            ct_ns = "http://schemas.openxmlformats.org/package/2006/content-types"
            registered_exts = set()
            for default in ct_root.iter(f"{{{ct_ns}}}Default"):
                registered_exts.add(default.get("Extension", "").lower())

            for img in media_images:
                ext = img.rsplit(".", 1)[-1].lower() if "." in img else ""
                if ext and ext not in registered_exts:
                    # JPEG can be registered as either "jpeg" or "jpg"
                    if ext in ("jpg", "jpeg") and ("jpg" in registered_exts or "jpeg" in registered_exts):
                        continue
                    errors.append(f"Image extension '.{ext}' (from {img}) not registered in [Content_Types].xml")
        except ET.ParseError:
            pass

    return errors


def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_docx.py <work_dir>", file=sys.stderr)
        sys.exit(1)

    work_dir = Path(sys.argv[1])
    if not work_dir.is_dir():
        print(f"Error: Not a directory: {work_dir}", file=sys.stderr)
        sys.exit(2)

    errors = []

    # Check required files
    for req in REQUIRED_FILES:
        if not (work_dir / req).exists():
            errors.append(f"Missing required file: {req}")

    # Validate all XML files
    for xml_file in work_dir.rglob("*.xml"):
        errors.extend(validate_xml_file(xml_file))

    # Also check .rels files
    for rels_file in work_dir.rglob("*.rels"):
        errors.extend(validate_xml_file(rels_file))

    # Validate image relationships
    errors.extend(validate_image_relationships(work_dir))

    if errors:
        print(f"Validation FAILED — {len(errors)} error(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)
    else:
        print("DOCX validation passed.", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
