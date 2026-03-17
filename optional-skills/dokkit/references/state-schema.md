# Dokkit State Schema

## state.json

```json
{
  "version": "1.0",
  "created": "2026-02-07T12:00:00Z",
  "updated": "2026-02-07T12:30:00Z",

  "sources": [
    {
      "id": "src_001",
      "file_path": "docs/sample_source/resume.pdf",
      "file_type": "pdf",
      "display_name": "resume.pdf",
      "content_path": ".dokkit/sources/resume.md",
      "metadata_path": ".dokkit/sources/resume.json",
      "summary": "Personal resume with education, work history, and skills",
      "status": "ready",
      "ingested_at": "2026-02-07T12:05:00Z"
    }
  ],

  "template": {
    "file_path": "docs/sample_template/template.docx",
    "file_type": "docx",
    "display_name": "template.docx",
    "work_dir": ".dokkit/template_work/",
    "set_at": "2026-02-07T12:15:00Z"
  },

  "analysis": {
    "path": ".dokkit/analysis.json",
    "total_fields": 22,
    "mapped": 18,
    "unmapped": 4,
    "analyzed_at": "2026-02-07T12:16:00Z",
    "image_fields": 2,
    "image_fields_sourced": 1,
    "image_fields_pending": 1
  },

  "filled_document": {
    "status": "review",
    "filled_at": "2026-02-07T12:20:00Z",
    "modifications": [
      {
        "instruction": "Change phone to 010-1234-5678",
        "fields_affected": ["field_005"],
        "modified_at": "2026-02-07T12:25:00Z"
      }
    ]
  },

  "exports": [
    {
      "format": "docx",
      "output_path": ".dokkit/output/filled_template.docx",
      "exported_at": "2026-02-07T12:30:00Z",
      "file_size": 45678
    }
  ]
}
```

## Field Definitions

### Root
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| version | string | yes | Schema version ("1.0") |
| created | string | yes | ISO 8601 timestamp of workspace creation |
| updated | string | no | ISO 8601 timestamp of last update |
| sources | array | yes | List of ingested source documents |
| template | object\|null | yes | Current template being filled |
| analysis | object\|null | yes | Template analysis metadata |
| filled_document | object\|null | yes | Filled document status |
| exports | array | yes | List of exports performed |

### Source Entry
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | yes | Unique identifier (src_NNN) |
| file_path | string | yes | Original file location |
| file_type | string | yes | Detected format |
| display_name | string | yes | Human-readable name |
| content_path | string | yes | Path to .md content file |
| metadata_path | string | yes | Path to .json sidecar |
| summary | string | yes | Brief content summary |
| status | string | yes | "processing" \| "ready" \| "error" |
| ingested_at | string | yes | ISO 8601 timestamp |
| error_message | string | no | Error details (when status=error) |

### Template
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file_path | string | yes | Original template location |
| file_type | string | yes | "docx" \| "hwpx" |
| display_name | string | yes | Human-readable name |
| work_dir | string | yes | Path to unpacked working copy |
| set_at | string | yes | ISO 8601 timestamp |

### Analysis
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| path | string | yes | Path to analysis.json |
| total_fields | integer | yes | Total fields detected |
| mapped | integer | yes | Fields with source mappings |
| unmapped | integer | yes | Fields without mappings |
| image_fields | integer | no | Total image fields detected |
| image_fields_sourced | integer | no | Image fields with source images |
| image_fields_pending | integer | no | Image fields awaiting images |
| analyzed_at | string | yes | ISO 8601 timestamp |

### Filled Document
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| status | string | yes | "filling" \| "review" \| "modified" \| "finalized" |
| filled_at | string | yes | ISO 8601 timestamp |
| modifications | array | no | List of modification records |

### Export Entry
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| format | string | yes | "docx" \| "hwpx" \| "pdf" |
| output_path | string | yes | Path to exported file |
| exported_at | string | yes | ISO 8601 timestamp |
| file_size | integer | no | File size in bytes |
| warnings | array | no | Conversion warnings |

## Valid Status Values

### Source Status
- `processing` — currently being parsed
- `ready` — successfully ingested
- `error` — parsing failed

### Filled Document Status
- `filling` — fields being mapped and filled
- `review` — filling complete, awaiting review
- `modified` — user requested changes
- `finalized` — user approved, ready for export
