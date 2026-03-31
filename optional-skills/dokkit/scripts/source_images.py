#!/usr/bin/env python3
"""Generate or search images for dokkit template filling.

Usage:
    python source_images.py generate \\
        --prompt "인포그래픽 제목: AI 감정 케어 플랫폼" \\
        --preset infographic \\
        --output-dir .dokkit/images/ \\
        --project-dir . \\
        [--lang ko] \\
        [--aspect-ratio 16:9] \\
        [--no-enhance]

    python source_images.py search \\
        --query "company logo example" \\
        --output-dir .dokkit/images/

Language options (--lang):
    ko        Korean only (default). All text in generated images will be Korean.
    en        English only. All text in generated images will be English.
    ko+en     Mixed Korean and English. Titles in Korean, technical terms in English.
    ja        Japanese only.
    <code>    Any ISO 639-1 language code.
    <a>+<b>   Mixed: primary language + secondary language.

    python source_images.py generate \\
        --prompt "인포그래픽 제목: AI 감정 케어 플랫폼" \\
        --preset infographic \\
        --output-dir .dokkit/images/ \\
        --project-dir . \\
        --field-id field_014 \\
        --purpose "스마트 관광용 AR앱 활용"

Output:
    Prints __RESULT__ JSON to stdout:
    {"image_id": "...", "file_path": "...", "source_type": "generated"|"searched",
     "field_id": "...", "purpose": "..."}

Requires:
    GEMINI_API_KEY in .env or environment variables.
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

# Model for image generation
IMAGE_MODEL = "gemini-3-pro-image-preview"

# Language display names for prompt injection
LANG_NAMES = {
    "ko": "한국어",
    "en": "English",
    "ja": "日本語",
    "zh": "中文",
    "es": "español",
    "fr": "français",
    "de": "Deutsch",
    "pt": "português",
}

# Preset-to-style mapping for prompt enhancement
PRESETS = {
    "technical_illustration": {
        "style": "깔끔한 기술 다이어그램 스타일. 선명한 선, 레이블이 있는 구성요소, 전문적인 색상.",
        "aspect_ratio": "16:9",
    },
    "infographic": {
        "style": "전문적인 인포그래픽 스타일. 아이콘 기반, 깔끔한 레이아웃, 기업용 색상 팔레트.",
        "aspect_ratio": "16:9",
    },
    "photorealistic": {
        "style": "사실적인 사진 스타일. 고품질, 자연스러운 조명.",
        "aspect_ratio": "4:3",
    },
    "concept": {
        "style": "개념적 일러스트레이션 스타일. 추상적/모던, 비즈니스 제안서에 적합.",
        "aspect_ratio": "1:1",
    },
    "chart": {
        "style": "깔끔한 차트/그래프 스타일. 정확한 데이터 시각화, 전문적 색상.",
        "aspect_ratio": "16:9",
    },
}


def load_api_key(project_dir: Path) -> str:
    """Load Gemini API key from .env or environment."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        return key
    env_path = project_dir / ".env"
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return ""


def build_lang_instruction(lang: str) -> str:
    """Build language instruction to append to the prompt.

    Args:
        lang: Language code. 'ko', 'en', 'ko+en', etc.

    Returns:
        Instruction string to append to the prompt.
    """
    if "+" in lang:
        parts = lang.split("+", 1)
        primary = parts[0].strip()
        secondary = parts[1].strip()
        primary_name = LANG_NAMES.get(primary, primary)
        secondary_name = LANG_NAMES.get(secondary, secondary)
        return (
            f"\n\n[언어 규칙] 이미지의 텍스트는 {primary_name}를 기본으로 하되, "
            f"기술 용어나 고유명사는 {secondary_name}를 사용할 수 있습니다. "
            f"제목과 설명은 반드시 {primary_name}로 작성하세요."
        )
    else:
        lang_name = LANG_NAMES.get(lang, lang)
        if lang == "ko":
            return (
                "\n\n[언어 규칙] 이미지의 모든 텍스트는 반드시 한국어로만 작성해야 합니다. "
                "영어 텍스트를 절대 사용하지 마세요. 제목, 라벨, 설명, 주석 등 "
                "모든 텍스트 요소를 한국어로 작성하세요."
            )
        elif lang == "en":
            return (
                "\n\n[Language Rule] All text in the image must be written in English only. "
                "Do not use any other language. Titles, labels, descriptions, and annotations "
                "must all be in English."
            )
        else:
            return (
                f"\n\n[Language Rule] All text in the image must be written in {lang_name} only. "
                f"Do not use any other language."
            )


def enhance_prompt(prompt: str, preset: str, lang: str, no_enhance: bool) -> str:
    """Enhance the prompt with preset style and language instructions.

    Args:
        prompt: User-provided prompt.
        preset: Preset name (e.g., 'infographic', 'technical_illustration').
        lang: Language code.
        no_enhance: If True, skip preset style enhancement (still apply lang).

    Returns:
        Enhanced prompt string.
    """
    parts = []

    if not no_enhance and preset in PRESETS:
        parts.append(f"[스타일] {PRESETS[preset]['style']}")

    parts.append(prompt)
    parts.append(build_lang_instruction(lang))

    return "\n\n".join(parts)


def generate_image(
    prompt: str,
    preset: str,
    output_dir: str,
    project_dir: str = ".",
    lang: str = "ko",
    aspect_ratio: str = "",
    no_enhance: bool = False,
) -> dict:
    """Generate an image using Gemini image generation model.

    Args:
        prompt: Image generation prompt.
        preset: Style preset name.
        output_dir: Directory to save the generated image.
        project_dir: Project root (for .env lookup).
        lang: Language code for text in images.
        aspect_ratio: Override aspect ratio (e.g., '16:9', '4:3').
        no_enhance: Skip preset style enhancement.

    Returns:
        Result dict with image_id, file_path, source_type.
    """
    proj = Path(project_dir).resolve()
    api_key = load_api_key(proj)
    if not api_key:
        return {"error": "GEMINI_API_KEY not configured. Set it in .env or environment."}

    # Enhance prompt
    full_prompt = enhance_prompt(prompt, preset, lang, no_enhance)

    # Resolve aspect ratio
    if not aspect_ratio and preset in PRESETS:
        aspect_ratio = PRESETS[preset]["aspect_ratio"]
    if not aspect_ratio:
        aspect_ratio = "16:9"

    # Build request
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{IMAGE_MODEL}:generateContent?key={api_key}"
    )

    # Add aspect ratio hint to prompt
    ratio_hint = f"\n\n[이미지 비율] {aspect_ratio} 비율로 생성해주세요."
    full_prompt += ratio_hint

    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"responseModalities": ["image", "text"]},
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        return {"error": f"Gemini API error ({e.code}): {body}"}
    except urllib.error.URLError as e:
        return {"error": f"Gemini API connection error: {e}"}

    # Extract image from response
    candidates = result.get("candidates", [])
    if not candidates:
        return {"error": "Gemini returned no candidates"}

    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        if "inlineData" in part:
            img_b64 = part["inlineData"].get("data", "")
            mime = part["inlineData"].get("mimeType", "image/png")
            if img_b64:
                img_bytes = base64.b64decode(img_b64)
                # Determine extension
                ext = ".png" if "png" in mime else ".jpg"
                image_id = f"gen_{uuid.uuid4().hex[:8]}"
                filename = f"{image_id}{ext}"

                out_path = Path(output_dir)
                out_path.mkdir(parents=True, exist_ok=True)
                file_path = out_path / filename

                with open(file_path, "wb") as f:
                    f.write(img_bytes)

                result = {
                    "image_id": image_id,
                    "file_path": str(file_path),
                    "source_type": "generated",
                    "file_size": len(img_bytes),
                    "lang": lang,
                    "preset": preset,
                    "prompt": prompt,
                    "model": IMAGE_MODEL,
                }
                return result

    return {"error": "No image data in Gemini response"}


def search_image(query: str, output_dir: str) -> dict:
    """Search for an image (placeholder — not yet implemented).

    Image search requires additional API setup. For now, returns an error
    directing the user to provide images manually.
    """
    return {
        "error": (
            "Image search is not yet implemented. "
            "Please provide images manually via '/dokkit modify \"use <file>\"'."
        )
    }


def parse_args(argv: list) -> dict:
    """Parse command-line arguments."""
    if len(argv) < 2:
        return {"error": "Usage: source_images.py <generate|search> [options]"}

    command = argv[1]
    args = {"command": command}

    i = 2
    while i < len(argv):
        arg = argv[i]
        if arg == "--prompt" and i + 1 < len(argv):
            args["prompt"] = argv[i + 1]
            i += 2
        elif arg == "--preset" and i + 1 < len(argv):
            args["preset"] = argv[i + 1]
            i += 2
        elif arg == "--output-dir" and i + 1 < len(argv):
            args["output_dir"] = argv[i + 1]
            i += 2
        elif arg == "--project-dir" and i + 1 < len(argv):
            args["project_dir"] = argv[i + 1]
            i += 2
        elif arg == "--lang" and i + 1 < len(argv):
            args["lang"] = argv[i + 1]
            i += 2
        elif arg == "--aspect-ratio" and i + 1 < len(argv):
            args["aspect_ratio"] = argv[i + 1]
            i += 2
        elif arg == "--query" and i + 1 < len(argv):
            args["query"] = argv[i + 1]
            i += 2
        elif arg == "--field-id" and i + 1 < len(argv):
            args["field_id"] = argv[i + 1]
            i += 2
        elif arg == "--purpose" and i + 1 < len(argv):
            args["purpose"] = argv[i + 1]
            i += 2
        elif arg == "--no-enhance":
            args["no_enhance"] = True
            i += 1
        else:
            i += 1

    return args


def main():
    args = parse_args(sys.argv)

    if "error" in args:
        print(json.dumps(args), file=sys.stderr)
        sys.exit(1)

    command = args.get("command")

    if command == "generate":
        prompt = args.get("prompt")
        if not prompt:
            print(json.dumps({"error": "Missing --prompt"}), file=sys.stderr)
            sys.exit(1)

        result = generate_image(
            prompt=prompt,
            preset=args.get("preset", "infographic"),
            output_dir=args.get("output_dir", ".dokkit/images/"),
            project_dir=args.get("project_dir", "."),
            lang=args.get("lang", "ko"),
            aspect_ratio=args.get("aspect_ratio", ""),
            no_enhance=args.get("no_enhance", False),
        )

        # Attach field_id and purpose if provided
        if "field_id" in args:
            result["field_id"] = args["field_id"]
        if "purpose" in args:
            result["purpose"] = args["purpose"]

        # Append to image manifest for tracking
        if "error" not in result:
            output_dir = args.get("output_dir", ".dokkit/images/")
            manifest_path = Path(output_dir).parent / "image_manifest.json"
            manifest = []
            if manifest_path.exists():
                try:
                    with open(manifest_path, "r", encoding="utf-8") as mf:
                        manifest = json.load(mf)
                except (json.JSONDecodeError, IOError):
                    manifest = []
            manifest.append(result)
            with open(manifest_path, "w", encoding="utf-8") as mf:
                json.dump(manifest, mf, ensure_ascii=False, indent=2)

    elif command == "search":
        query = args.get("query")
        if not query:
            print(json.dumps({"error": "Missing --query"}), file=sys.stderr)
            sys.exit(1)
        result = search_image(
            query=query,
            output_dir=args.get("output_dir", ".dokkit/images/"),
        )
    else:
        result = {"error": f"Unknown command: {command}. Use 'generate' or 'search'."}

    # Output result with __RESULT__ marker for agent parsing
    print(f"__RESULT__{json.dumps(result, ensure_ascii=False)}")

    if "error" in result:
        sys.exit(1)


if __name__ == "__main__":
    main()
