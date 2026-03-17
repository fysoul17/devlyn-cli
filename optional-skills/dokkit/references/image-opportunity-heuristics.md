# Image Opportunity Heuristics for Section Content Fields

Guide for detecting image insertion opportunities within `section_content` fields. These heuristics help the analyzer identify where AI-generated images can be interleaved with text to create visually rich proposals.

## Content Signal Keywords

Scan the `mapped_value` text for these signal keywords that indicate an image would add value.

### By `content_type`

| content_type | Korean keywords | English keywords |
|---|---|---|
| flowchart | 프로세스, 절차, 단계, 흐름, 순서, 워크플로우 | process, procedure, step, flow, workflow, pipeline |
| diagram | 구조, 아키텍처, 시스템, 모듈, 구성도, 체계 | architecture, structure, system, module, framework, topology |
| data | 시장규모, 성장률, 통계, 수치, 비율, 점유율, 매출 | market size, growth rate, statistics, data, ratio, share, revenue |
| concept | 개념, 비전, 전략, 핵심, 모델, 방법론, 기술 | concept, vision, strategy, core, model, methodology, technology |
| infographic | 비교, 장점, 특징, 차별점, 효과, 기대효과 | comparison, advantage, feature, differentiation, effect, benefit |

### Signal strength

- **Strong signal** (2+ keywords in same paragraph): high-priority opportunity
- **Moderate signal** (1 keyword): include if surrounding context supports it
- **Weak signal** (keyword in passing mention): skip unless the paragraph is >300 chars

## Placement Rules

### Where to insert

- **After the paragraph** that introduces the concept — not before, not mid-paragraph
- `insertion_point.strategy` = `"after_paragraph"`
- `insertion_point.anchor_text` = a distinctive phrase (5-15 words) from the paragraph that signals the concept. Choose a phrase that is unique within the field's mapped_value.

### Where NOT to insert

- Never as the first element (before any text)
- Never as the last element (after all text)
- Never between two consecutive images (min 150 chars of text between image opportunities)
- Never inside bulleted/numbered list sequences
- Never right after a heading (insert after the explanatory paragraph instead)

## Prompt Composition Strategy

For each detected opportunity:

1. **Read the anchor paragraph** in Korean
2. **Identify the core concept** being described
3. **Compose an English generation prompt** that:
   - Describes the visual content (what to show)
   - Specifies the style (technical diagram, data chart, concept illustration)
   - Includes domain context (e.g., "for a government R&D proposal")
   - Avoids text/labels in the image (these are hard to control)
4. **Map to a preset**: `technical_illustration` (default for diagram, flowchart, concept), `infographic` (for data, infographic)

### Prompt template

```
[content_type] showing [core concept from paragraph].
Context: [section name] of a Korean government R&D project proposal.
Style: Clean, professional, minimal text labels.
Color scheme: Modern, corporate blue/teal tones.
```

## Skip Conditions

Do NOT create image opportunities when:

1. **Short content**: `mapped_value` < 400 characters total
2. **Team/personnel lists**: Content is primarily names, roles, and qualifications (look for patterns like `이름:`, `직책:`, `담당:`, `학력:`, `경력:`)
3. **Budget/financial tables**: Content is primarily numbers, amounts, costs (look for `원`, `만원`, `억원`, `비용`, `예산`)
4. **Already has explicit image fields**: If the section already contains `field_type: "image"` fields in analysis.json, reduce max opportunities to 1
5. **Simple form data**: Content is short key-value pairs without narrative text
6. **Repeating field**: If the same section has multiple `section_content` fields that overlap in content

## Limits and Spacing

| Constraint | Value |
|---|---|
| Max opportunities per `section_content` field | 3 |
| Min chars before first opportunity | 200 |
| Min chars between opportunities | 150 |
| Min total mapped_value length | 400 chars |
| Max total opportunities across all sections | 12 |

## Output Schema

Each opportunity is added to the field's `image_opportunities` array:

```json
{
  "opportunity_id": "imgop_{field_id}_{seq}",
  "insertion_point": {
    "strategy": "after_paragraph",
    "anchor_text": "AI 유사도 탐색 알고리즘을 통해 기존 특허와의 유사성을 분석"
  },
  "generation_prompt": "Technical architecture diagram of an AI-powered IP similarity search system showing document ingestion, vector embedding, and similarity matching pipeline. Context: Korean government R&D proposal. Style: Clean, professional, minimal text. Color: Modern blue/teal.",
  "preset": "technical_illustration",
  "content_type": "diagram",
  "rationale": "Text describes the AI algorithm workflow; a diagram clarifies the system architecture",
  "dimensions": {
    "width_hwpml": 36000,
    "height_hwpml": 24000,
    "width_emu": 4572000,
    "height_emu": 3048000
  },
  "image_file": null,
  "status": "pending"
}
```

### Field meanings

- `opportunity_id`: Unique ID, format `imgop_{field_id}_{sequence_number}`
- `insertion_point.strategy`: Always `"after_paragraph"` for section content
- `insertion_point.anchor_text`: Distinctive Korean phrase from the paragraph (used by filler to locate insertion point)
- `generation_prompt`: English prompt for AI image generation
- `preset`: Maps to `scripts/source_images.py` preset parameter
- `content_type`: One of `flowchart`, `diagram`, `data`, `concept`, `infographic`
- `rationale`: Brief explanation of why an image helps here
- `dimensions`: Default size — filler may adjust based on content_type
- `image_file`: `null` until sourced (set by fill-doc orchestrator)
- `status`: `"pending"` → `"sourced"` → `"inserted"` (or `"skipped"`)
