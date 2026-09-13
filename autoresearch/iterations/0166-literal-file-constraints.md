# 0166 — Literal file constraints

2026-09-13. Root executes the authorized sequential core work directly; actual
Fable5.1 and Grok4.6 review read-only. Baseline ee9f185a6b4e564ae3b29cbd547ed814d5687792.
Prospective receipt3512513c0efd116a18ef82b0 owns branch and scratch.

## Observation and scope

Historical0157 authored `requirements*.txt` / `**/requirements*.txt` exclusions,
but the checker uses literal membership. Ten registered current component
controls reproduce that mismatch and preserve legitimate literal-star names.
Schema and authoring guidance now say literal paths; patterns/directory exclusions
use suitable verification commands. No glob expansion or invalid-star ban.

Inspection then found a separate underlying defect: changed_files stripped and
split human Git output. Its two consumers are expected_contract_findings and
BUILD_GATE authorized_surface_findings. Seven actual CLI controls reproduced
five missed names (Korean, tab, newline, leading/trailing space). The named scope
delta is recorded in source-decision.json; initial prediction remains intact.

No guesswork / No workaround: live enumeration uses Git NUL output and
--no-renames; external enumeration uses Git's parser-only numstat in both
directions. Errors become visible findings in both consumers. Dedup prevents
two scope findings per edit. A parsed external rename/copy covers both names
appearing in its headers; live copy recognition remains disabled. No patch is
applied, and binary/mode-only changes are included.

The default parser strips one prefix component. An actual nested no-prefix
patch silently returned app.py for src/app.py. The candidate requires Git a/b
headers, makes the producing bootstrap force those prefixes, and documents the
external format. It does not guess strip depth. Supplied external bytes remain
unchanged. Empty bytes mean no changes; malformed/prefix-invalid input fails.

## Controls and subtraction

Fifteen actual names/changes include Unicode, whitespace, quote, backslash,
literal star, rename source/destination, deletion, mode and binary edits.
Baseline live7/15 and external4/15; candidate15/15 both. All declared paths pass
PLAN scope. Ten initial literal/glob semantics remain unchanged. The first
coverage apparatus placed the PLAN marker after its heading and failed early;
its original script and failure description are retained, then corrected to the
actual section contract. Earlier CLI apparatus also omitted the BUILD_GATE
plan; its corrected VERIFY isolation and original failure are retained.

Candidate self-test passes. A regression block exercises both consumers,
rename, duplicate findings, external format, binary placeholder, CRLF, copy,
empty/malformed patches and invalid base. POSIX-only filenames are skipped on
Windows, where those names are invalid; Korean/internal-space still run.
Four isolated deletions (NUL, reverse, dedup, prefix guard) each fail an assertion.
No existing checks were removed. No overengineering: no pattern engine, fallback
parser, new flag or runtime phase. Added checks cover observed failures.

Native design reviewers independently rejected the first external candidate.
Root adopted prefix enforcement and dedup. Actual Git controls disprove the
suggested binary-placeholder/CRLF failures and confirm reverse copy-source
reporting. Review disagreement is resolved by raw execution, not consensus.
Fable5.1 actual recovery is confirmed; no substitute needed for0166.
The first final reviews were Fable PASS_WITH_ISSUES339.429s / Grok PASS408.174s.
Root reproduced Fable's ambient apply.whitespace=error false block (exit128 with
valid path stdout); --whitespace=nowarn gives exit0. Final candidate adds that
argument and a regression. A non-UTF8-content control also reproduces the old
UnicodeDecodeError; final reader detects the forbidden file instead. Adjacent
forbidden_patterns semantics and optional caching are deferred, not silently
changed. Exact Git path guidance and rename coverage are clarified.

## Acceptance and boundaries

Full skill lint passes324.241s and272.645s. The second final review is Fable
PASS_WITH_ISSUES / Grok PASS. Root reproduced the remaining producer issue:
ambient diff.external=true emitted zero bytes for a tracked edit. A final
--no-ext-diff flag preserves the native Git patch; the existing bootstrap test
now also checks that POSIX configuration. Final whole-bootstrap self-test passes.
Final delta Fable PASS_WITH_ISSUES39.155s / Grok PASS83.003s;
root accepts PASS_WITH_ISSUES with zero in-scope CRITICAL/HIGH. All eight native
source reviews used zero tools. The final low findings concern throwaway-fixture
abort hygiene and pre-existing textconv hunk semantics; neither changes literal
path enumeration. Whole-source CI must run before merge; prior local lint is
not attributed to bytes changed afterward.
Evidence `.devlyn/0166/`; delivery evidence remains separate and must establish
exact accepted commit, Linux/Windows CI, packaged bytes, merge and owned cleanup.
No native author draw, semantic-recall gain, current routing adherence or broad
bare/solo/pair advantage follows from these deterministic component controls.
Original project WIP, A16 and frozen comparisons stay untouched; no npm release.
