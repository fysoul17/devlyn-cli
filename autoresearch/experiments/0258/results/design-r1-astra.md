**MEDIUM 5건, LOW 1건으로 수정 후 동결을 권합니다.** 검정력 계산과 D3 witness의 기본 실현 가능성은 확인됐습니다.

1. **MEDIUM — C 패키지의 삭제 대상 목록이 실제 배포물과 다릅니다.**

   **정확한 문구:** [DESIGN.md:24](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-clause-ablation/autoresearch/experiments/0258/DESIGN.md:24)의 “from every shipped copy”와 네 경로, 104행의 “the four deletions above”.

   **근거:** 고정된 `0257-live/control/packages/B/package`에는 해당 절이 `AGENTS.md`, `CLAUDE.md`, `config/skills/_shared/runtime-principles.md`에 각각 한 번 있습니다. 패키지 안의 `.agents/skills/_shared/runtime-principles.md`는 없습니다. 설치기가 `config/skills`에서 설치 대상의 skill 디렉터리로 복사합니다. 따라서 명시한 네 번의 삭제를 검증하는 패키지 diff 검사는 통과할 수 없습니다.

   **수정:** 패키지 원본의 **세 곳 삭제**로 명시하고, 설치 결과의 `.agents` 및 `.claude` runtime-principles에도 삭제가 반영되는지 별도로 검증하십시오. 동일 절의 모든 전달 경로를 수정하는 것은 추가 처치가 아닙니다. 다만 추정 대상은 AGENTS 단독이 아니라 패키지에 실린 해당 절입니다.

2. **MEDIUM — C 실행과 Claude 전용 자격 검증에 필요한 apparatus 변경이 빠져 있습니다.**

   **정확한 문구:** [DESIGN.md:97](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-clause-ablation/autoresearch/experiments/0258/DESIGN.md:97)의 “Unchanged from 0257 … the instruction-load assertion”와 102–113행의 변경 목록.

   **근거:**

   - `0257/prepare.py:145`는 A/B만 허용하며, 170행은 B에만 패키지를 설치합니다.
   - `0257/run_cell.py:236`은 측정 실행 전에 Claude와 Codex 양쪽의 sealed forms를 요구하고, 262행은 모든 arm에 B 패키지 digest를 기록합니다.
   - `0257/instructions.py:139`는 기존 B-only forms와 네 A/B×engine SMOKE를 전제로 합니다.
   - 공통 `0256/control.py:25`는 B만 빌드합니다. `judge.py:23`도 `NX01_0257_RUNTIME`을 사용합니다.

   **수정:** `control`, `prepare`, `instructions`, `run_cell`, judge의 필요한 변경을 명시하십시오. C의 수정된 tree identity를 별도로 봉인하고, B/C 각각 올바른 패키지를 설치한 두 Claude SMOKE가 측정 실행 gate를 통과하는 통합 자격 검사를 추가하면 됩니다. **No workaround**에 따라 기존 gate를 우회하지 않고 새 arm 구조에 맞춰야 합니다.

3. **MEDIUM — P1에 존재하지만 평가 불가능한 결과의 처리 규칙이 없습니다.**

   **정확한 문구:** [DESIGN.md:76](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-clause-ablation/autoresearch/experiments/0258/DESIGN.md:76)의 “a missing probe, witness or mandatory judgment”.

   **근거:** 기존 `judge.py:102–119`는 timeout, 프로세스 실패, 잘못된 출력을 **존재하는** `class: 'unassessable'` 결과로 저장합니다. 이는 “missing”이 아닙니다. 단순히 JSON-400 개수를 세면 실행 오류가 음성 관측으로 들어갈 수 있습니다. 0257 DESIGN 258–261행은 이 경우 예측을 채점하지 않는다고 명시했습니다.

   **수정:** 32개 F10 결과 모두 `json_error_400`, `html_400`, `other` 중 하나여야 한다고 고정하십시오. 누락·잘못된 형식·`unassessable`은 `NOT_FINISHED`, p-value 없음으로 처리하고, 동일 트리에서의 재실행 규칙도 미리 정하십시오.

4. **MEDIUM — D3 witness는 가능하지만 실패와 재현을 구별하는 정확한 계약이 필요합니다.**

   **정확한 문구:** [DESIGN.md:62](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-clause-ablation/autoresearch/experiments/0258/DESIGN.md:62)의 “rewrite one token … it reproduces when the override has no effect”.

   **근거:** 읽기 전용 메모리 내 실행으로 일반 operand를 `before`→`after`로 바꾸고 `parse(['before'], { from: 'user' })`를 호출했습니다.

   | 기존 트리 | override 호출 | 최종 operand | 재현 |
   |---|---:|---|---|
   | d241 | 0 | before | 예 |
   | d049 | 0 | before | 예 |
   | d002 | 1 | after | 아니요 |
   | d017 | 1 | after | 아니요 |

   따라서 제시한 자격 검증 트리들은 적절합니다. 다만 기존 `judge.py:68–70`은 exit 1을 재현으로 취급하므로, 처리되지 않은 Node 예외도 재현으로 잘못 집계될 수 있습니다.

   **수정:** 정확한 argv, operand, 기대 출력, 호출 기록과 판정 조건을 고정하십시오. 예상하지 않은 예외는 exit ≥2 및 unresolved로 구분하고, SMOKE 전에 스크립트를 봉인하십시오.

5. **MEDIUM — 안전성 항목의 gating 여부와 예측 채점이 충돌합니다.**

   **정확한 문구:** [DESIGN.md:68](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-clause-ablation/autoresearch/experiments/0258/DESIGN.md:68)의 “Reported, never gating: … false completions, scope violations, user-data harm”와 78행의 “C_UNSAFE: any C cell has …”.

   **근거:** 같은 항목이 비-gating과 최우선 안전성 gate로 동시에 정의됩니다. 또한 90행의 “Holm-rejected (CLAUSE_IMPLICATED)”는 안전성 우선순위와 동치가 아닙니다. P1이 기각돼도 headline은 `C_UNSAFE`일 수 있습니다.

   **수정:** 안전성 우선순위를 유지한다면 세 안전성 항목을 never-gating 목록에서 빼십시오. 예측 1의 `(CLAUSE_IMPLICATED)`는 삭제하고 P1 기각 자체로 채점하십시오. 완료된 unsafe 실행에서도 P1/P2 결과는 token에 남도록 명시하면 해석이 분명합니다.

6. **LOW — D3 전용 judge 명령은 필요하지 않습니다.**

   **정확한 문구:** [DESIGN.md:110](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-clause-ablation/autoresearch/experiments/0258/DESIGN.md:110)의 “and its `judge.py` command”.

   **근거와 수정:** 기존 `judge.py run <witness> <cell>...`이 임의의 Node witness를 지원합니다. **No overengineering**에 따라 새 명령 대신 기존 `run`을 사용하면 됩니다.

통계 검산은 모두 설계와 일치합니다.

| 계산 | 정확한 값 |
|---|---:|
| P1 검정력: .50 대 .05, α=.025 | 0.777258 |
| P1 검정력: .30 대 .05, α=.025 | 0.311111 |
| P2 검정력: .625 대 .25, α=.025 | 0.436528 |
| 같은 P2, α=.05 | 0.586447 |
| Fisher 8 대 0 | 0.00122358 |
| Fisher 4 대 0 | 0.05061179 |

두 검정의 Holm family는 타당합니다. 제시한 검정력은 첫 threshold 기준이며, 안전성까지 포함한 headline 발생 확률은 아닙니다.

동시 bare arm은 이 좁은 B–C 비교에 필요하지 않습니다. 교대하는 인접 실행은 순서 효과를 줄이지만, 실행 중 모델·계정 변화까지 통제하지는 않으므로 replicate와 계정별 분포를 보고해야 합니다. P1/P2는 진단된 **행동 차이**를 측정하며, 모델이 그 선택을 한 내부 이유까지 입증하지는 않습니다.

기존 B의 instruction bytes/forms는 재사용할 수 있고, `instruction-templates.json` 재생성은 필요 없습니다. 운영상 amendment 2를 그대로 상속하면 SMOKE 전 85/70, 이후 등록된 변경으로 95/95가 됩니다. grading은 측정 owner 64회에 assessor 최소 128회와 추가 adjudication이 필요하며, 이는 현재 설계에 포함된 부담입니다.

VERDICT: REVISE
