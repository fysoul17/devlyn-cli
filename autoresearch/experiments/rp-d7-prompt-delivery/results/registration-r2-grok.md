# rp-d7 registration review r2 — Grok 4.7

I'll review the registration read-only: round-1 findings first, then the apparatus commit and input hashes, and only then whether anything new is wrong.Round-1 asked for three fixes: unscored second clause, a verbatim Decision copy, and prediction wording. I'll read the current registration against DESIGN and the summarizer.The three round-1 fixes are visible in the text. Next I’ll check that `apparatus_commit` is the commit that holds this apparatus and that each input hash matches that commit.Round-1 fixes hold. The second prediction clause stays unscored whenever any skip’s tag set is unset, including next to a counterexample. The Decision and prediction bodies match DESIGN.md byte for byte, and the assurance now says there is no positive prediction support while outcomes are unknown.

`apparatus_commit` `d49ebb63f28a82bbfe06cd6b308250ffcb53ad5c` is the commit that holds this apparatus. All 16 `inputs` SHA-256 values match that commit’s blobs and the current files. Later registration edits do not change those files.

VERDICT: SHIP
