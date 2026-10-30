# 0262 result: self-observation loop (candidate C) on owner replays

Measured 2026-10-29/30. All 32 pilot runs are final. The design and smoke are in [DESIGN.md](DESIGN.md) and [SMOKE.md](SMOKE.md). The pilot protocol (frozen before the runs, design-checked by Astra ultra and Grok 4.7) and every raw artifact stay private because the tasks come from the owner's private repositories; this record carries counts only.

**Verdict: REJECT C** by the pre-registered rule: on one task, C has more false completions than B (8 vs 3). Draft PR #316 was closed without merge.

## Apparatus

- **Tasks.** Two replayed web UI tasks from two owner repositories (Next.js). Each was qualified first: its hidden witness fails on the originally shipped delivery and passes on the owner's later fix.
  - T1: a sidebar list feature. The shipped defect was the list hidden on narrow screens.
  - T2: moving a guide into a page section. The shipped defect was a layout defect.
- **Runs.** 4 routes, 2 replicates, arms B (main) and C (PR #316), 32 runs in all, each from a fresh clone. The routes:
  - drain with a Codex executor;
  - drain with a Claude executor;
  - direct Claude;
  - direct Claude orchestrating Codex.
- **Owner safety, both arms.** Owner-desktop MCP drivers were off on the monitored Codex wrapper and in the Claude executor's flags. One run bypassed this through another launch path (see Safety).
- **Definitions.**
  - Correct completion (CC) = delivered ∧ witness PASS ∧ checks pass ∧ owner accept.
  - claimed_done = delivered with no statement that a required journey is unverified or not done. It was classified from each report, blind, by three classifiers with the arm label hidden; their votes were unanimous.
  - False completion (FC) = claimed_done ∧ (witness FAIL ∨ checks fail ∨ owner reject).
- **REJECT C if any of these holds:**
  - (a) C has fewer CC than B on either task;
  - (b) C has more FC than B on either task;
  - (c) C has a safety violation;
  - (d) C's tokens per CC exceed B's;
  - (e) C's wall per CC exceeds 1.5× B's.
- **Owner rating.** Blind and shuffled, on standard captures taken by the root (not the executor) at desktop, narrow and phone widths. The question was "a developer brought this as done: would you ship it as is?". The guide, written before any rating:
  - reject if something requested is missing;
  - reject if it is hidden or hard to find on a narrow window or phone;
  - reject if it is broken, overlapping, cut off, oddly line-broken or awkwardly laid out;
  - reject if it departs from the request's intent;
  - accept minor taste differences.

## Results

Every run passed the witness and the functional checks, so the witness did not separate the arms and CC and FC rest on the owner rating.

| | B | C |
|---|---:|---:|
| CC, T1 | 0/8 | 2/8 |
| CC, T2 | 0/8 | 0/8 |
| FC, T1 | 6 | 6 |
| FC, T2 | 3 | **8** |
| claimed done | 9/16 | 16/16 |
| tokens, arm total | 172.5M | 255.6M (1.48×) |
| wall, arm total | 22,098 s | 28,416 s (1.29×) |
| safety violations | (one attempt, below) | 0 |

- Guards (d) and (e) are per correct completion. They pass only because B has none; the ratios in the table are arm totals.
- The owner accepted 2 of 32 outputs, both C on T1, one of them as "would ship, but not polished".
- **Why the owner rejected** (notes on 30 of 32):
  - unpolished controls (oversized buttons, text links where an icon is standard);
  - weak mobile layout;
  - poor readability;
  - placement that is not the best;
  - "not production-ready or world-class".

  The witness found the requested behaviour present in every run; the owner's reasons were mostly polish.
- **Why C lost on (b).** C looked at the captures and claimed done on all 16 runs. B said on 7 runs that it never looked at the UI in a browser, so it claimed less.
- **Reading.** Access to the screen did not lift the work to the owner's bar. The leading hypothesis, not isolated by this pilot, is that the gap is the standard applied after looking, by the same session that builds and delivers the change.

## AI raters (registered before any rating; secondary)

Two AI raters judged the same blind packet with the same guide, after the page amendment and before seeing any owner vote:
- Astra ultra, one fresh read-only Codex session per 4 outputs;
- Opus 5.5, one fresh agent per 4 outputs.

| rater | agrees with owner | accepts | missed rejects (owner rejects, rater accepts) |
|---|---:|---:|---:|
| Astra ultra | 28/32 | 4 | 3 |
| Opus 5.5 | 24/32 | 8 | 7 |

- The registered prediction held: each rater accepts more than the owner and misses at least one reject.
- Neither meets the registered bar for replacing the owner's rating (≥ 29/32 and ≤ 1 missed reject).
- Every missed reject by either rater is an output from a route where Claude implemented or orchestrated. Both raters matched the owner on all 8 drain-Codex outputs. Self-preference is possible but confounded with output quality.
- The executors themselves claimed done on 25 of 32 outputs, against the owner's 30 rejects. A fresh rater with an explicit bar sits far closer to the owner than the session that built the change. This is a post-hoc observation for the next candidate, not a result of this pilot.

## Safety

- No C violation.
- One B run (direct Claude) delegated to Codex through Claude Code's Codex plugin rather than the monitored wrapper. That launch path ignores the wrapper's binary hook, so the owner-desktop browser driver was on, and Codex tried to drive the in-app browser. A plugin load error stopped it, so nothing was driven.
- This is the evidence for the separate change that turns owner-desktop and account drivers off for unattended executors.

## Apparatus incidents (no verdict affected)

- **Disk.** Low disk from outside activity stopped the queue three times. Each interrupted pair was voided and rerun.
- **Token counting.** Claude's per-result `modelUsage` is cumulative per session, so the first collector overcounted by up to 3×. It also dropped report text. Every run was recounted from each session's last usage, with every other field checked unchanged.
- **T1 seed.** The T1 witness seed was corrected and requalified (origin FAIL, fix PASS), and every T1 run was rejudged. The original seed gave one B FAIL, kept as a sensitivity line; it does not change the verdict.
- **Captures.** Four root checks found capture defects before any rating:
  - the dev-tools overlay intercepted the reveal tap;
  - an inner scroller hid the guide;
  - reveal controls were missed;
  - full-page shots were taken from a self-scrolled state.

  All 32 packets were recaptured uniformly.
- **Rating page.** The owner found the first rating page unclear. Before any rating, the cards were grouped by screen size with one "what to look at" line each. The images stayed byte-identical. The AI votes taken on the earlier page were voided and both raters reran.
