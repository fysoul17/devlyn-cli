# State Management

Protocol for reading and writing `.dokkit/state.json`. All agents follow this protocol.

## Workspace Structure

```
.dokkit/
├── state.json          # Single source of truth for session state
├── sources/            # Ingested source content
│   ├── <name>.md       # Extracted content (LLM-optimized markdown)
│   └── <name>.json     # Structured metadata sidecar
├── analysis.json       # Template analysis output (from analyzer)
├── images/             # Sourced images
├── template_work/      # Unpacked template XML (working copy)
│   ├── word/           # (DOCX) or Contents/ (HWPX)
│   └── ...
└── output/             # Exported filled documents
    └── filled_<name>.<ext>
```

## Reading State

Read `.dokkit/state.json` before any operation. Check:
- `sources` array for available context
- `template` for current template info
- `analysis` for field mapping data
- `filled_document` for current document status

## Writing State

After any mutation:
1. Read current state.json (avoid overwriting concurrent changes)
2. Update only the relevant fields
3. Write the full state back
4. Validate: `python .claude/skills/dokkit/scripts/validate_state.py .dokkit/state.json`

## State Transitions

```
/dokkit init → state created (empty)
/dokkit ingest → source added to sources[]
/dokkit fill or fill-doc → template set, analysis created, filled_document created
/dokkit modify → filled_document updated
/dokkit review approve → filled_document.status = "finalized"
/dokkit export → export entry added to exports[]
```

## Validation

The validator checks:
- Schema conformance
- Required fields present
- Valid status values
- Source file references exist
- No orphaned entries

## References

See `references/state-schema.md` for the complete schema definition.
