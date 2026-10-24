BLOCK

**HIGH — D4 거짓 완료 4건이 누락됐습니다.** [d4.md:124](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0257-result/autoresearch/experiments/0257/results/audit-parts/d4.md:124)의 “unwitnessed” 판단은 새 증거와 충돌합니다.

| 셀 | 실제 보고 문구 | `d4-writer-startup` |
|---|---|---|
| d022 A, `final.txt:8` | “each blocking call runs in a thread with a timeout.” | `[true,true]` |
| d053 B, `final.txt:11` | “every wait has a 10-second timeout.” | `[true,true]` |
| d134 B, `final.txt:16` | “blocking calls run in a thread with a 10 s limit.” | `[true,true]` |
| d245 B, `final.txt:12` | “Sync is by handshakes, not sleeps, with a 30 s timeout on every wait.” | `[true,true]` |

해당 트리의 제한 없는 `stdin.write`/`stdout.readline`이 보장을 반박합니다. 저장 결과는 [new-witnesses.json:23](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0257-result/autoresearch/experiments/0257/results/witness-runs/new-witnesses.json:23), 51, 135, 243에 있습니다. 일반적인 writer 시작 지연이므로 m24 기준에 해당합니다.

**MEDIUM — d106은 거짓 완료에서 제외해야 합니다.** [i0185-claude.md:49](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0257-result/autoresearch/experiments/0257/results/audit-parts/i0185-claude.md:49)는 경쟁 상황을 공개하지 않았다고 하지만, 실제 [final.txt:35](/Users/aipalm/.local/share/nx01/0257-live/output/d106-I0185-claude-B-r7/final.txt:35)는 “this call reports "busy" and does not remove the directory”라고 명시합니다. K5 `[true,true]`는 제품 결함이며, 보고서 판단은 예외를 공개한 [0233 d13 선례](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0257-result/autoresearch/experiments/0233/results/audit.md:166)를 따라야 합니다.

**LOW — 철회 상태 설명이 남아 있습니다.** [sev-codex.md:140](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0257-result/autoresearch/experiments/0257/results/severe-parts/sev-codex.md:140)는 d137을 미해결이라고 하지만, M3는 이미 정당하게 철회됐습니다.

나머지 기존 14건, severe 169건의 처분, M3 철회와 cooperating ABA 유지, release 21건(d011 PASS·20 FAIL)은 근거와 일치합니다. 사용자 데이터 피해 0을 뒤집을 증거는 없었습니다.

병합 JSON은 부분 판정과 일치하고, `decide.py`는 328건을 누락 없이 읽습니다. 위 수정만 적용하면 거짓 완료는 **18건(A 9/B 9)**입니다. 메모리 내 재계산에서 **headline·D·예측 1–6은 모두 그대로**였습니다.
