# AF1 completed Claude helper audit

Read-only audit after d15's final verdict, 2026-10-10. No model invocation, frozen-input change, historical regrading or candidate decision. A/B/C all pass the five AF1 oracle rows and local delivery. All existing QA files and `matching/crossmatch_reserver.py` are byte-identical to the registered baseline in all three evaluated snapshots; d15 changes only `visible/intake/hold_intake.py`. Complete hashes and original costs are in [cells.json](cells.json).

## Recorded boundaries

| Cell | Owner seconds | Processed input incl. cache | Output | First product Edit after owner start |
| --- | ---: | ---: | ---: | ---: |
| d14 A | 855.364 | 1,305,743 | 86,558 | 565.497 s |
| d15 B | 1218.138 | 5,192,478 | 122,560 | 559.745 s |
| d13 C | 1169.674 | 3,809,320 | 116,734 | 722.738 s |

The B trace does **not** show sixteen minutes spent only orienting before touching the product. Its first product Edit is at 03:50:04.358 UTC, 559.745 seconds after the owner run began. Later helper investigation follows completed product edits and public/scenario checks. The A native owner also takes 565.497 seconds before its first Edit, despite making no delivery-helper calls. A first-Edit boundary is descriptive; it does not separate necessary reasoning from wasted effort.

Source transcripts (line numbers below refer to these retained JSONL files):

- C: [c0478063-e1fd-4b33-81f2-8fc1e20b27f7.jsonl](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/d13-EQ3-AF1-claude-C-r1/home/.claude/projects/-cell-work/c0478063-e1fd-4b33-81f2-8fc1e20b27f7.jsonl). First Edit line 106; helper scan/read calls 73, 79, 83, 90, 93, 95.
- A: [0c26ce3e-f939-44c5-a3f4-4c88f3f23a8a.jsonl](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/d14-EQ3-AF1-claude-A-r1/home/.claude/projects/-cell-work/0c26ce3e-f939-44c5-a3f4-4c88f3f23a8a.jsonl). First Edit line 46; local commit line 97.
- B: [522ec03e-496c-4737-8c1e-40de3d38ac31.jsonl](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/d15-EQ3-AF1-claude-B-r1/home/.claude/projects/-cell-work/522ec03e-496c-4737-8c1e-40de3d38ac31.jsonl). First Edit line 107; helper scan/read calls 80, 86, 91, 96; later delivery dry-run/diagnostic calls 133, 138, 141, 146, 151, 154, 159, 163, 168.

## Bounded accounting

Before this deterministic calculation, the prediction was recorded in the tool transcript: selected tool subprocess spans would be much shorter than surrounding elapsed gaps; response usage could be associated with calls but could not isolate counterfactual helper-only cost. Raw calculations confirm it.

Each tool elapsed value is its assistant tool-use timestamp to its matching user tool-result timestamp. Sum is observed tool-call latency, not model reasoning time. Response usage deduplicates native assistant message IDs, using the last usage envelope for each selected call-emitting message. It includes that response's full cached context and any preceding reasoning. It is **not marginal helper cost**, and selected result text can also reappear in later cached input.

| Observed group | Calls / unique responses | First call to last result | Summed tool latency | Returned UTF-8 bytes | Call-emitting processed input | Call-emitting output |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| C helper scan/read | 6 / 5 | 14.728 s | 0.359 s | 54,725 | 456,757 | 8,000 |
| B helper scan/read | 4 / 4 | 13.410 s | 0.065 s | 64,421 | 344,649 | 27,349 |
| B later delivery dry-run/diagnosis | 9 / 9 | 229.640 s | 0.810 s | 9,686 | 1,515,236 | 31,626 |

C's combined task-completion/runtime-principles read at line 57 returns 17,647 bytes in 0.051 seconds. B's task-completion read at line 44 returns 15,270 bytes in 0.020 seconds; its runtime/engine documents are separate calls. The response emitting C's document read already contains 42,272 output tokens, so assigning that entire response to the document it has not yet received would plainly overstate document-induced cost. These envelopes cannot establish how many tokens or seconds deleting a helper read would save.

## What the completed evidence supports

1. **A real restriction prompted the source inspection.** B explicitly scans for Git config writes, push/fetch and network calls at line 80, then reads helper source. C makes a similar scan at line 79. The participant request prohibits changing Git configuration and network use except model calls. The frozen delivery document says the local path fetches/pushes nothing ([task-completion.md:53](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/d15-EQ3-AF1-claude-B-r1/cell/work/.claude/skills/_shared/task-completion.md:53)); it does not explicitly state the local helper's Git-configuration behavior. This is an observed uncertainty, not evidence that every inspection was necessary or that a new sentence will save time.
2. **The dry run exposed an actual cleanup condition.** B's dry-run `complete --local-only` succeeds but reports scratch `RETAINED` due to unknown process access (line 142). Its diagnostic finds `/proc/304/fd` denied for a same-user zombie `git`, PPid 1 (line 147). It later measures stable inode numbers on the mounted checkout (lines 163–169), then performs the real local delivery (175–190). This is distinct from redundant reading. The separately admitted cleanup fix was not installed in these frozen B/C cells, so their times do not evaluate that fix.
3. **Do not promise that the entire local workflow never writes the config file.** During the dry run, allocation and completion preserve the config hash/inode/mtime (lines 139, 142). `git branch -d` during reconciliation changes its inode/mtime while retaining identical bytes (lines 151–152). The frozen document explicitly instructs branch deletion at [task-completion.md:74](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/d15-EQ3-AF1-claude-B-r1/cell/work/.claude/skills/_shared/task-completion.md:74). A statement about the helper's local allocation/completion must not silently become a guarantee about all Git reconciliation commands or hooks/configurations.
4. **Source confirms a narrower fact only.** The local allocation branch skips remote policy and reconciliation ([task-complete.py:199](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/d15-EQ3-AF1-claude-B-r1/cell/work/.claude/skills/_shared/task-complete.py:199)); local completion returns before the remote policy/publication branch ([task-complete.py:686](/Users/aipalm/.local/share/nx01/0237-live/out-discovery/d15-EQ3-AF1-claude-B-r1/cell/work/.claude/skills/_shared/task-complete.py:686)). Helper source uses `git config --local --get-all` for a read, not a configuration setter. Root has decided not to add a no-Git-configuration-writes claim. This audit does not justify disabling restriction checks or adopting a blanket no-audit rule.

## Cleanup-specific B/C contrast

Both B and C actually receive the same `unknown process access` / scratch `RETAINED` condition. C receives it once on real completion (line 173), checks custody/refs and confirms the scratch has zero entries (175–176), reconciles the original checkout (180–181), and reports the retained scratch. C performs no `/proc` diagnostic and no copied-repository delivery rehearsal. Its custody-check call takes 0.039 seconds and returns 985 bytes; its call-emitting response records 173,089 processed input / 1,354 output, again not marginal cost.

B first encounters the condition in its rehearsal (142). The clearest cleanup-specific extra call is the purpose-written `/proc` scan (146–147); a later receipt/empty-scratch inspection is mixed with checking that the actual repository remains untouched (154–155). Together those two selected calls take 0.118 seconds and return 3,173 bytes. Their two call-emitting responses record 336,920 processed input / 6,172 output. They are a subset of the nine-call group above, not additional costs to sum into it. Allocation/commit rehearsal happened before the returned cleanup condition and cannot be attributed to that condition. Subsequent branch reconciliation, hooks/config checks and mounted-inode checks address other restrictions or receipt identity as well; the 224.768 seconds from B's first retention result to its real allocation is therefore an enclosing interval, not a causal cleanup surcharge.

The observed difference is specific: B investigates a condition that C retains and reports. Correcting the already-admitted helper failure removes that trigger in a future baseline. Consequently this one C/B resource difference may not transfer to the best accepted harness. A future candidate comparison must use that accepted baseline; do not subtract these associated response counts or elapsed intervals from either historical owner total.

C is slightly cheaper than B in this single completed draw; A is faster and cheaper than both. The call boundaries do not establish the cause of that difference. All three products satisfy these five AF1 predicates; none of these observations establishes candidate admission, general engine superiority, or full PR/merge delivery.
