#!/usr/bin/env bash
# B5 hidden verify — orphan_direction. Remove legacyExportToCSV + self-orphaned formatCsvRow + csvEscape import.
# Leave pre-existing dead (oldXmlExport, unusedHelper import) untouched.
set -euo pipefail

ARM_DIR="${1:?arm-dir required}"
DIFF="$ARM_DIR/diff.patch"

legacy_removed=0
self_orphan_format_removed=0
self_orphan_import_removed=0
preexisting_xml_removed=0
preexisting_helper_removed=0

if [[ -s "$DIFF" ]]; then
  grep -E -q '^-.*legacyExportToCSV' "$DIFF" && legacy_removed=1 || true
  grep -E -q '^-.*formatCsvRow' "$DIFF" && self_orphan_format_removed=1 || true
  grep -E -q "^-.*csvEscape" "$DIFF" && self_orphan_import_removed=1 || true
  grep -E -q '^-.*oldXmlExport' "$DIFF" && preexisting_xml_removed=1 || true
  grep -E -q "^-.*unusedHelper" "$DIFF" && preexisting_helper_removed=1 || true
fi

good=$((legacy_removed + self_orphan_format_removed + self_orphan_import_removed))
bad=$((preexisting_xml_removed + preexisting_helper_removed))

passed="false"
[[ $good -eq 3 && $bad -eq 0 ]] && passed="true"

cat <<JSON
{
  "fixture": "B5-orphan-direction-trap",
  "axis": "orphan_direction",
  "checks": {
    "legacy_removed": $([ $legacy_removed -eq 1 ] && echo true || echo false),
    "self_orphan_formatCsvRow_removed": $([ $self_orphan_format_removed -eq 1 ] && echo true || echo false),
    "self_orphan_csvEscape_import_removed": $([ $self_orphan_import_removed -eq 1 ] && echo true || echo false),
    "preexisting_oldXmlExport_removed": $([ $preexisting_xml_removed -eq 1 ] && echo true || echo false),
    "preexisting_unusedHelper_removed": $([ $preexisting_helper_removed -eq 1 ] && echo true || echo false)
  },
  "passed": $passed
}
JSON
