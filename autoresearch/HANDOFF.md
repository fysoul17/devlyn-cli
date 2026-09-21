# Core harness improvement — 0200 terminal run ID validation

2026-09-21 KST. Root direct; **no resolve, including controls**. No npm release.
Retained checkout: `/Users/aipalm/.local/share/nx01/core-continuation-20260912`.
Read [0200](iterations/0200-terminal-run-id.md), then `.devlyn/0200/FINAL.md`
for verification, delivery and cleanup. Receipt `319c348e34180e5ce36e49e4`.

0195's dot-dot candidate reproduces a current false completion: `run_id: ".."`
lets the active state serve as its own archive. The classifier now rejects exactly
`.` and `..` before archive lookup; valid dotted IDs remain supported. Invalid
same-session open states now follow the Stop hook's existing MALFORMED/allow policy.
Product verification and delivery remain separate; FINAL owns their actual status.

0199 is COMPLETE at PR76, and0198 at PR75. Their frozen records are unchanged:
no observed fresh-context lift or overall completion ranking, no R1 adoption.
Both0198 branch witnesses remain mandatory for future R1 validation. Do not rerun
exposed0197–0200 tasks as untouched confirmation or add generic reminders.

Mission1, unrelated confirmation and field gate15 remain OPEN;0187 NO-GO and
existing routing stand. Next work needs a supported core failure or untouched
natural comparison. Preserve original checkout WIP, source/Git, participant data,
frozen records and A16. Clean only prospectively owned disposable scratch.
