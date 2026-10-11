# s01-h-claude-v3 protocol audit

2026-10-10. Bounded read-only audit of the finalized cell at
`/Users/aipalm/.local/share/nx01/0238-live/staged-v1/out-smoke-v2/s01-h-claude-v3`.
Paths below are relative to that directory. No protocol blocker observed in this
operational smoke. This does not establish automatic activation or pair efficacy.
No models, authentication, tests or native commands were run; original evidence
and verdicts remain unchanged. Input hashes, accounting and seals are root's
separate audit scope.

- **Unfiltered request and role.** `cell/work/.devlyn/pair/request.md:7` contains
  the entire 2,424-character `harness/caller.json` request exactly once. It is
  followed by candidate diff at line 17 and raw checks at line 97; owner
  interpretation starts at line 173. The leading role instruction confines the
  peer to read-only review. The complete request file equals both the launcher's
  prompt argument and the peer's native user message (peer transcript below,
  line 3). This verifies actual transmission, not merely a prepared file.
- **Actual fresh and resumed identity.** Fresh and resume captures in
  `cell/work/.devlyn/pair/review1/` and `review2/` both name session
  `8c5719a5-0b60-487f-90ec-fa88921b769c`, with completed native results,
  `is_error=false` and `modelUsage` containing only `claude-opus-5-5`.
  The resume attempt explicitly uses that exact session. In
  `home/.claude/projects/-cell-work/8c5719a5-0b60-487f-90ec-fa88921b769c.jsonl`,
  every one of the 16 real assistant rows records model `claude-opus-5-5` and
  top-level effort `max`, including fresh rows 15–41 and resumed rows 49–53.
  The owner's real assistant rows also record that same model and effort.
  This conclusion uses native messages, not requested-route receipts alone.
- **Stable source and completed answers.** All four source identity objects
  (fresh before/after and resume before/after) are exactly equal. Both helper
  completions are EXITED/0, with `source_unchanged=true`; elapsed times are
  174.738909623s and 9.409959922s. The owner reads the entire fresh answer in
  `run/stdout:763–764`, then the entire resumed answer at lines 798–799;
  both returned tool results contain the corresponding complete answer text.
- **Executable proposed check.** The fresh answer proposes
  `calculate_total(105, 10, 10) == 105`; the resumed answer recalls and confirms
  it. The owner executes that assertion at `run/stdout:828–829`, obtaining
  stdout `105` and exit 0, retained in
  `cell/work/.devlyn/pair/owner-check-peer-proposals.txt:1–3`. The same check
  is recorded again against the delivery worktree at `run/stdout:968–969`.
  No audit rerun was performed.
- **Lifecycle and restricted peer.** The native task events mark both calls
  foreground (`run/stdout:734`, `795`) and completed (`740`, `796`) before
  the owner continues. Both peer native results and the owner terminal result
  (`run/stdout:1107`) report zero spawned children. The peer's only observed
  tools are Read, Grep and Glob. The marker check reports `CLAUDECODE` present
  at `run/stdout:741`; the invocation at line 733 does not remove it.
  The process diagnostic at lines 896–897 shows only the owner Claude process;
  its initial LIVE matches are the diagnostic shell/awk itself, not a peer.
  Successful awaited exits plus final clean container teardown support no
  remaining background peer; no post-run live process probe was needed.
- **Local attribution.** `delivery.json` records commit
  `b98b7e85153c62e1378d1ff5bf46343d8062f807`, parent/allocation
  `8e983432f66a4db6190d921c001b48caf7f89204`, and only
  `calculate_total.py`/`test_calculate_total.py` changed. Before commit,
  `run/stdout:969` records the staged diff identical to the peer-reviewed diff;
  lines 976 and 1027 retain commit/blob and local-only custody evidence.
  Lines 1048–1050 record fast-forward reconciliation, worktree/branch removal
  and a clean final main checkout. No publication is shown or claimed.

The old v2 DNS failure and UNKNOWN cost remain separate retained evidence. This
successful smoke supplies fresh/resume transport and lifecycle evidence only.
