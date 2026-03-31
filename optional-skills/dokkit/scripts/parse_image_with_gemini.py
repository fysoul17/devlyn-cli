#!/usr/bin/env python3
"""Parse image files using Google Gemini Vision API for OCR and content extraction.

Usage:
    python parse_image_with_gemini.py <input-image> [--project-dir <dir>]

Output:
    JSON to stdout with 'content_md' and 'metadata' fields.

Requires:
    GEMINI_API_KEY in .env or environment variables.
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


def load_api_key(project_dir: Path) -> str:
    """Load Gemini API key from .env or environment."""
    # Check environment first
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        return key

    # Check .env file
    env_path = project_dir / ".env"
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip()

    return ""


def parse_image(file_path: str, project_dir: str = ".") -> dict:
    """Parse an image using Gemini Vision API."""
    path = Path(file_path)
    proj = Path(project_dir).resolve()

    api_key = load_api_key(proj)
    if not api_key:
        return {"error": "GEMINI_API_KEY not configured. Set it in .env or environment."}

    # Read and encode image
    with open(path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    # Determine MIME type
    ext = path.suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".webp": "image/webp", ".gif": "image/gif"}
    mime_type = mime_map.get(ext, "image/png")

    # Call Gemini Vision
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

    payload = {
        "contents": [{
            "parts": [
                {"text": (
                    "Extract ALL text from this image. Preserve the layout as much as possible. "
                    "If there are tables, convert them to markdown tables. "
                    "If there are form fields, identify labels and values. "
                    "Output the extracted content as clean markdown. "
                    "Also identify any key-value pairs (like Name: John) and list them at the end "
                    "in a section called '## Extracted Key-Value Pairs' as a markdown table."
                )},
                {"inlineData": {"mimeType": mime_type, "data": image_data}}
            ]
        }]
    }

    req = urllib.request.Request(
        f"{url}?key={api_key}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": f"Gemini API error ({e.code}): {body}"}
    except urllib.error.URLError as e:
        return {"error": f"Gemini API connection error: {e}"}

    # Extract text from response
    candidates = result.get("candidates", [])
    if not candidates:
        return {"error": "Gemini returned no response"}

    parts = candidates[0].get("content", {}).get("parts", [])
    extracted_text = ""
    for part in parts:
        if "text" in part:
            extracted_text += part["text"]

    if not extracted_text.strip():
        return {"error": "No text could be extracted from the image"}

    # Parse key-value pairs from the extracted text
    key_value_pairs = {}
    lines = extracted_text.split("\n")
    for line in lines:
        if ":" in line and not line.startswith("#"):
            parts_split = line.split(":", 1)
            label = parts_split[0].strip().strip("|").strip()
            value = parts_split[1].strip().strip("|").strip()
            if label and value and len(label) < 50:
                key_value_pairs[label] = value

    content_md = f"# {path.stem}\n\n{extracted_text}"

    return {
        "content_md": content_md,
        "metadata": {
            "file_name": path.name,
            "file_type": ext.lstrip("."),
            "parse_date": datetime.now().isoformat(),
            "key_value_pairs": key_value_pairs,
            "sections": ["OCR Content"],
            "parse_method": "gemini_vision",
        }
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_image_with_gemini.py <image> [--project-dir <dir>]",
              file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]
    project_dir = "."
    if "--project-dir" in sys.argv:
        idx = sys.argv.index("--project-dir")
        if idx + 1 < len(sys.argv):
            project_dir = sys.argv[idx + 1]

    if not Path(file_path).exists():
        print(json.dumps({"error": f"File not found: {file_path}"}))
        sys.exit(1)

    result = parse_image(file_path, project_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
