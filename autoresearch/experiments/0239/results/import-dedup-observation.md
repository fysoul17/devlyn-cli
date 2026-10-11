# Direct AGENTS import detection — investigation, not admission

2026-10-10. Read-only follow-up while the ordinary lifetime cell runs. No
installer mutation, reproduction, native import probe or performance claim yet.
This does not change the frozen 0239 comparison or its two-fix baseline.

`bin/instructions.js:123` recognizes only a whole line `@AGENTS.md` outside
fences. `bin/devlyn.js:764` uses this result to decide whether CLAUDE.md should
hold its own defaults. Both inline imports and `@./AGENTS.md` therefore miss
that recognition in the current source. The existing portability tests around
lines405–502 cover the exact-line positive, fenced negative, duplicate removal,
reinstallation and the AGENTS-to-CLAUDE self-import exception.

The official [Claude memory documentation](https://code.claude.com/docs/en/memory#import-additional-files),
retrieved2026-10-10, describes relative imports in ordinary prose, excluding
Markdown code spans and fenced blocks. Earlier project memory from the H9/H10
audit (entry4d5c55d1-7caf-5f6c-86c3-259f779b56c7,2026-10-06) records the same
inline/relative gap and a then-current native whitespace-prefixed import parser.
The later duplicate-removal/self-import fix (5b086f96-fb95-5d72-b483-4ba1762d13b2)
is present and must be preserved; the earlier H10 duplicate-block bug is not
assumed still open. Current official documentation is not proof of every detail
of the pinned CLI's parser.

Prediction for a subsequent disposable installer reproduction: a direct inline
or `./` import beside an AGENTS.md containing current defaults will leave two
defaults blocks, whereas the exact-line form leaves one. Confirm actual native
recognition before changing the detector. Preserve code-span/fence negatives,
other filenames, self-import behavior, user prose, backups and idempotent
updates. Prefer the smallest justified parser change; no manual downstream
file repair, broad Markdown subsystem or empirical token-saving claim follows
from this static observation. Any accepted fix must be packaged into the later
pair baseline; it must not alter either frozen 0239 arm or their scores.
