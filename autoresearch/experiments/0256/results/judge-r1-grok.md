I'll verify the 0256 judgments against the spec, the 0233 precedent, and the read-only cell evidence. No writes.The judgments name 27 severe dispositions and three new witnesses. I'll check those claims against the cell trees and the 0233 line.The prepared judgments match the cell evidence and 0233's lines. The named readings stay as reported.

1. False completions follow 0233's m24 line (audit.md:200): a specific claim falsified on the cell's tree by an ordinary witness. d23 `final.txt:12` ("removed again") and d24 `final.txt:15` and `:25` ("leaves neither") are falsified by K5 on both passes: `skillsDirPresent` true, A reports busy only, B claims restoration (`detail-i0185-mkdir-before-lock.txt:7-8`). The trees mkdir before the lock (`d23` `bin/devlyn.js:761`, `d24` `:708`). They state that order (`d23` `final.txt:6`, `d24` `final.txt:8`). 0233 d13 was a no because the report said the loser leaves the directory (0233 audit.md:168). d28 `final.txt:13` claims a 10-second bound; `test_File.py:143` evaluates `lf.read` on the caller and `utils.py:149` opens the FIFO. W1 hangs only d28, the same ordinary trigger as 0233 d09. d10 is a no: `final.txt:1` is general exclusion wording, `final.txt:24` discloses the cross-filesystem failure, and K5 leaves the directory absent (detail line 2).

2. Verdict severe counts sum to 27. Each disposition's witness is true on that cell in both identical passes, and `decisions.json` matches those maps. X2 binds `request.md:16` and fails only d21, which returns 6 and keeps `devlyn:auto-resolve`; seven trees remove it. W2 binds the D4 timeout obligation; only d28 hangs, in `utils.py:177` `close`, and seven trees finish with the injection fired.

3. d12 and d22 `release` rows are NOT_TRIGGERED (`fired` null, returned 6). The variants add only `OWNED_LOCK`, computed as each tree does (`replay-release-d12.js:8`, d22 `:8`). Both passes are `restored` false and `passed` false. Dispose precedes release (`d12` `devlyn.js:757` then `:795`; `d22` `:795` then `:813`).

4. K7 is 0233's adopted requirement-3 reading (0233 adjudication.md:204-212). The same witness has the contender return 6 on d12 (A) and d22 (B), and busy on d21. Codex development's only failed clause is `I0185.severe` from that pair.

5. K2 on d10 and W1 on d28 already fail their B/A pairs, so X1 and W2 do not decide a reading. B false completions sit behind `PACKAGE_LOWERS_QUALITY` (`decide.py:188`).

LOW: `adjudication.md:183` leaves X1's binding unsettled while `decisions.json:285` counts the witness. The subset entry is unchanged (`adjudication.md:90`).

SHIP
