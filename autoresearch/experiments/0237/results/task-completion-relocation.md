# Proposed task-completion policy paragraph relocation

2026-10-10. Proposed docs-only patch; canonical and installed mirror files are
unchanged. No new behavior, helper change, product-policy change or measured
performance claim.

## Exact change

Apply `task-completion-relocation.patch` from the repository root when approved
for implementation. It moves the existing implicit no-GitHub-origin LOCAL_ONLY
paragraph verbatim from lines 61–64 to lines 18–21, immediately after the
policy paragraph ending at line 16. It makes the identical move in:

- `config/skills/_shared/task-completion.md`
- `.agents/skills/_shared/task-completion.md`

One existing blank separator moves with the paragraph. The rest of each
file is byte-identical after excluding that relocated block. No text is added,
removed or rephrased. Default automatic PR/merge, explicit-request blocking,
and the prohibition on using authentication/network/configuration failures as
fallback grounds all remain unchanged.

## Preservation receipt

Both original files are byte-identical, as are their proposed results.

| Property, per file | Before | Proposed |
| --- | ---: | ---: |
| Bytes | 14434 | 14434 |
| Whitespace-delimited words | 2006 | 2006 |
| Lines | 235 | 235 |
| Paragraph line range | 61–64 | 18–21 |

- Original SHA-256: `dac27a1c4434aa059282628bdd14420ebfa59b155129e318dcdedf8cd3cd44b7`.
- Proposed SHA-256: `6466c18211c9bcea62dc3f72f2c4e2c745f86ce6eb08a12e1146dc4e9a0c4733`.
- Moved paragraph: 42 words, 294 bytes including its final
  newline; 295 bytes with the following blank separator.
- Whole-file byte and word multisets are identical; whole-file SHA changes
  because ordering changes. Removing the same unique relocated block from
  either version yields byte-identical remainder, a stronger content check
  than counts alone.

## Observed reader behavior

Raw root: `/Users/aipalm/.local/share/nx01/0233-live/out/`.

- `e02-E1-claude-B-r1/run/stdout:12`: actual Bash command reads
  `cat .claude/skills/_shared/task-completion.md 2>/dev/null | head -60`.
  Line 13 contains the returned first 60 lines and omits the fallback condition.
  Final lines 21–22 say changes remain uncommitted because default PR/merge
  requires network access prohibited by the caller.
- `e03-E1-claude-C-r1/run/stdout:9`: actual Bash command reads `git remote -v`
  and the same first 60 documentation lines. Line 10 shows local-path origin
  `/harness/mirror.git` and omits the fallback condition. Final lines 23–24 leave
  the changes uncommitted, citing network and allowed-file restrictions.
- The installed historical `.claude/skills/_shared/task-completion.md` first
  65 lines are byte-identical to the current canonical first 65 lines in both
  cells. This is the same observed document layout, not an inferred similarity.

The proposed first 60 lines include the **whole** condition at lines 18–21:
implicit delivery, absence of a GitHub origin, LOCAL_ONLY reporting, explicit
PR/merge refusal, and excluded fallback grounds. They do not claim to contain
the complete delivery workflow. Readers may still need to read later commands.

This establishes a concrete contract-visibility improvement for the observed
truncated reads. It does not prove that relocation alone would change those
owners' decisions: their interpretation of caller restrictions could remain
an independent obstacle. Source-solving quality, latency and token improvement
are unmeasured.

## Review and verification scope

No new tests are authored or executed for this reversible paragraph move.
The generation checks preserve every content byte and word; `git apply
--check` validates applicability without changing either file. A single
cross-model review is deferred to the owner. Existing coupled policy tests
will run if the patch is applied. The earlier broad 24-cell behavioral matrix
was a prospective research proposal, not a prerequisite for this docs-only
visibility correction and not an overridden admission rule. Any later solver
performance claim still needs its separately registered comparative evidence.
