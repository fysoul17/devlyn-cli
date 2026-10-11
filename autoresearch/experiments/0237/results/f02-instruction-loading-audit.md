# f02 instruction loading: root dedup is active; one explicit reread is redundant

Read-only audit, 2026-10-10. Only the finished f02 cell and repository source were inspected. No auth/model call, active-cell inspection, CLI execution, product change or new measurement.

**The native evidence does not support two full root instruction injections.** It does establish that the owner later requested the same principles again through an explicit runtime-guide read. This is narrower than a loader defect or a measured token-saving opportunity.

Raw cell: `/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f02-CF-CONFIG-claude-C-r1-auth1`.

Native transcript: `home/.claude/projects/-cell-work/5c6e3d25-f0ba-4254-9450-03b949092a3b.jsonl` within that cell.

| Native evidence | What it establishes |
| --- | --- |
| Transcript line 10, `attachment.type=instructions`, `rendered` | Two file entries are rendered: `/cell/work/CLAUDE.md` contains only `@AGENTS.md`; `/cell/work/AGENTS.md` contains the full installed instructions. The rendered instruction message contains exactly **one** `## North Star` and one copy of the North Star/core-principles body. |
| Transcript lines 15 and 24, `attachment.type=prompt_snapshot` | Saved native system-prompt blocks contain no additional North Star body. The only instructions attachment in this owner transcript is line 10. |
| Transcript lines 29–30; equivalent `run/stdout:10–11` | The owner explicitly calls `cat` on both completion and runtime guides. The runtime tool result contains the same North Star/core-principles body, byte-for-byte, once more. This repeated body is **2,966 characters / 2,989 UTF-8 bytes**, excluding the runtime-guide preamble. |

These are recorded native rendered instructions and a delivered tool result, not an inference from plugin names or filesystem presence. The `files[].content` metadata and `rendered` copy within one attachment must not themselves be counted as two prompt injections. The builtin `cc-plugin-agents-md` entry does not establish a second independent load; the preserved rendered message shows only one full body. This audit does not attribute the observed import resolution specifically to that plugin.

Existing product dedup explains the root shape. `bin/devlyn.js:762–784` detects an importing CLAUDE.md whose AGENTS.md holds the defaults, creates `@AGENTS.md` for a new CLAUDE.md where appropriate, and updates CLAUDE.md without a second defaults block. `bin/instructions.js:122–130` recognizes the import outside fenced code. f02's installed CLAUDE.md actually is the small import file, rather than a second full template.

The runtime mirror also already declares its restricted purpose: `config/skills/_shared/runtime-principles.md:3` says it supplies the principles for a context without the installed block. `config/skills/devlyn-ideate/SKILL.md:13` explicitly says to read it only when no block is loaded. f02 did not read/invoke that skill. The actual initial request (`native transcript:3`), pre-read rendered instructions and other startup attachments (`:4–15`), both saved system-prompt snapshots (`:15,24`), and the direct completion guide contain no instruction to read `runtime-principles.md`; the root block points to the completion guide only. The filename appears in the initial repository file listing (`:23`), followed by the owner's own read (`:29`, description “Read project policy docs for delivery”). This supports **owner-selected policy verification, not a required direct-work loading step**. It was in the same Bash call as the necessary delivery guide, so this record does not establish an avoidable extra tool round trip.

**Remaining hypothesis:** avoid an explicit runtime-principles reread when the owner already has the identical root block. This concrete repetition exists in f02, but a new general loading/dedup mechanism is not supported: root dedup and the mirror's fallback purpose already exist. Deleting either engine's root entrypoint or the fallback mirror is not justified by this observation. Repetition may also reinforce compliance; no behavioral counterfactual was measured.

There is no native per-fragment token attribution here, no measured wall/token saving, and no proof that this body remained duplicated in every later request. No token count was estimated from characters. The API wire payload and provider-side processing were not separately captured, so claims are limited to the native rendered context and returned tool text. AF1 and pinned loader code were unnecessary once this evidence was found and were not inspected.
