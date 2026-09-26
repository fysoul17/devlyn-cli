# 0221 — 책임 단위 축소, `/devlyn:intent`로의 full 교체 평가, 세션별 실행 계약

2026-09-24. **상태: CLOSED (2026-09-26, Session 8).** 0224 구조 스크린이 B′·C 모두 계속시키지 않아(`SCREEN:B'=none;C=none`) §5 row 8 탈락 분기로 끝났다: `/devlyn:intent` 후보는 제거, full resolve는 이행 규칙대로 유지(0224에서 완수는 입증되지 않음), T1b b1·b2·b4·b5 정리. Session 7·9는 실행하지 않는다. 등록 당시: 이 unit은 설계·등록만 한다. 제품 변경과 모델 실행은 없다.

- **작성 과정:** root Opus 5.5 + Astra(gpt-6-astra, reasoning ultra, read-only, isolated).
  - 방향 합의: 독립 R0 두 개 → R1 → R2 → R3 → R4 FREEZE.
  - 사용자 결정 반영 개정: 독립 R0 두 개 → R1 → Astra REVISE 전부 채택 → 최종 확인.
- **근거 수집:** 증거 리더 6 + 적대적 검증자 6, work packet 스코핑 6 + 검증자 6.
- **원시 기록:** `.devlyn/0221/`(토론 전문, 증거 요약, packet JSON).
- **세션용 작업 명세:** [experiments/0221/packets/](../experiments/0221/packets/README.md).

## 1. 진단 요약

- **효율:** 하네스는 효율을 깎아 왔다.
  - 0202 이전 full은 native 대비 wall 5–18×, OUTPUT 6–10×였다. 이 수치는 3.2.0 이전 것이고, **현행 3.2.x full은 native와 측정된 적이 없다.**
  - 상시 지침 + direct 경로는 Codex에서 시간 +20%, input +78%를 쓰고 완료 수는 같았다(0182).
- **품질:** 쉬운 작업에서는 동률이었다. 과잉 오케스트레이션이 품질을 떨어뜨린 기록이 있다: 0064 FS1, 0068–0078, 0140, 0169, 0183, 0075.5 SURFACE_CLOSE rollback.
- **가치가 반복 확인된 메커니즘:** 어려운 작업의 review→재현→수리(0184, 0185, 0175 H, 0187). 얇은 지침도 일부 표본에서 개선했다(0180, 0181).
- **하위 티어:** 하네스 vs bare 측정이 없다. 지침 효과는 모델별로 양방향이었다(0072, 0099).
- **연구가 제품 결정으로 이어지지 않은 이유:**
  - 0206 이후 21 PR에서 런타임 `bin/`·`config/` 변경이 없었다(3.2.1 버전 변경만 있음).
  - 0210 이후 모든 스크린이 descriptive-only로 계약됐다.
  - stop-all 규칙 때문에 참가 셀이 D1(포화)에 집중됐다(D1 19회, D2 1회 — 0218 D2-1-A 중단). D3/D4는 0회였다.
  - 8/1 이후 제품 커밋 111개 중 순감소는 2개다.
- **위반된 불변식:**
  - 연구 장치 개선은 유한한 비용 안에서 제품 선택을 가능하게 해야 한다.
  - 추가와 삭제 모두 위험에 맞는 증거를 요구해야 한다(0069.3, `DECISIONS.md:195`).

## 2. 사용자 결정 (2026-09-24, 원문)

1. full 교체도 고려하고 있어. 너무 비효율적이라서. 이미 intent 라고 짓지 않았어?
2. 예산을 초과하는건 사실 상관이 없지 않아? 테스트 용도면 그대로 해도 되는데, 굳이 하네스에 예산을 한정지을 필요는 없어
3. 실제로는 claude 는 opus 5.5 (이후에 fable 5.2 +가 나오면 바뀔수 있음) + sonnet 도 일부 가벼운 작업들. codex는 어려운 추론 설계등은 astra, 구현은 sol 도 가능. 그리고 grok.
4. 예산은 중요하지 않고 알아서 너무 과도하지 않고 충분히 테스트 해서 결과가 나올 정도.
5. 다른건 제안대로. 작업 후에 자동 PR 까지만.
6. 설계는 astra 와 함께 한번 논의하고, 새 세션에서 하나씩 할수 있도록 준비.

**해석:**
- `/devlyn:intent`는 0201:169-171에서 권고 명칭이었고 스킬은 없었다. 이번 결정으로 **이름을 확정한다.**
- full 교체가 범위에 들어왔으므로 0201 rule 5(full을 대조군으로도 쓰지 않음)는 **이 비교의 arm F에 한해 해제**한다.
- 전달 기본값은 push + PR이다. merge는 사용자가 한다.

## 3. 제품 목표 — `/devlyn:intent`

**커널(4책임):**
1. 사용자 계약(원문 요구·범위·명시적 선택)을 우선한다.
2. native owner가 구현하고 실제 검사를 실행한다.
3. 필요할 때 반례→재현→수리→재검증을 거친다.
4. 실패·미완료·증거 누락을 성공으로 바꾸지 않는다.

guard는 대상 실패가 구조상 불가능해졌음을 보인 뒤에만 지운다(0164, 0184, `docs/specs/iter0112-verdict-authority-chain/spec.md:13-37`).

| 표면 | 계약 |
|---|---|
| `/devlyn:intent "<goal>"` | 필요한 요구 확인 → 구현·검사 → 필요한 검토·수리 → PR |
| `--plan-only` | ideate의 요구 정렬·계획 기능(`--quick`/`--from-spec`/`--project`·출력 위치 매핑). 구현으로 넘어가지 않음 |
| `--spec <path>` | spec·expected를 보존하며 실행. 파일 입력이라는 이유로 고정 phase를 강제하지 않음 |
| `--verify-only <ref> --spec <path>` | 검토 전용. 수정·PR 없음 |
| `--goal-file`, `--engine`, `--role-config`, executor pin | 기존 의미·우선순위 보존. 미지원·미가용은 fail closed |
| `/devlyn:queue` | 유틸리티 유지. 실행은 intent에 위임. 같은 실패를 spec 재작성으로 반복하지 않음 |
| `/devlyn:engines`, `/devlyn:design-ui` | 유지 |

- **지울 것:** 의무적 중간 spec 생성, 고정 phase 전이 보고, 중복 요구 복사, 모델의 hash·usage 재조립, SURFACE_CLOSE, 자동 risk-probes, complexity 분류기, phase 생애주기 ceremony. 항목별 근거와 크기는 [packets/I1](../experiments/0221/packets/I1-resolve-responsibility-map.md)에 있다.
- **지우지 않을 것:** VERIFY pair default-when-available(NORTH-STAR:269, 사용자 승인 예외)은 유지한다.
- **새로 만들지 않을 것:** scheduler, DSL, 상태 머신.

**이행 규칙:**
- 채택된 경우에만 **다음 major**에서 intent를 기본으로 만든다.
- `resolve`/`ideate` 옛 이름은 한 major 동안 **안내 전용**으로 둔다. 새 의미로 자동 실행하지 않는다.
- `resolve --spec`의 명시적 full 의미를 조용히 바꾸지 않는다.
- 옛 task-completion 경로와 구버전 재개 방법을 보존한다.
- 폐기 옵션은 무시하지 않고 명시적으로 멈춘다.
- 후보가 탈락하면 full을 유지한다. 이름만 바꾼 배포를 교체 성과라고 부르지 않는다.

## 4. 실험 계약 (예산 한정 없음)

### 삭제·유지·정지 조건

- **삭제:**
  - 셀/전체 token·OUTPUT·호출·금액 cap
  - 자식 4회·리뷰 2회 제한(같은 입력의 무변화 반복 재시도는 중단)
  - first-breach stop-all, reviewer-timeout stop-all
  - 0218 meter 읽기 의무, 0214 wait 문장, 0220 reserve 문장·`last_generation_input` 예측
  - 공통 계약의 사용량 보고 의무와 모델의 hash·로그·사용량 조립
- **유지:**
  - watchdog: 작업 90분, 개별 검토 10분. timeout 시 결과·가용 사용량을 보존하고 다음 셀로 진행
  - 사후 사용량 기록: 누락은 UNKNOWN이며 0으로 쓰지 않음
  - 사용량 누락과 reviewer timeout은 별도 필드로 기록
- **전체 정지 조건:** 자식 종료 미확인, 저장소 격리·모델 identity·공통 evaluator 붕괴일 때만.
- **보존:** 과거 중단 결과는 재해석하지 않는다.

### arm과 구성

- **arm:**
  - A: 강한 native
  - B′: intent 후보
  - C: native + 일반 review→repair
  - F: published `devlyn-cli@3.2.1` full. 릴리스 merge `13f1833`..`466aa25` 사이 `config/ bin/ CLAUDE.md AGENTS.md` diff가 없다. tarball integrity와 컨테이너 내 기본 full 실행은 S3에서 검증한다.
- **주 구성 2개:**
  - Claude 구성: `claude-opus-5-5`가 owner·구현·primary 검토를 맡고, OTHER 검토는 `gpt-6-astra`.
  - Codex 구성: `gpt-6-astra`가 owner·primary 검토, `gpt-6-sol`이 구현을 맡는다. codex worker model 지정은 role-config.py:130-135가 이미 허용한다. OTHER 검토는 `claude-opus-5-5`.
- **경량 경로:** `claude-sonnet-5` 또는 `gpt-6-sol`을 owner로 실행한다.
- **`grok-4.7`:** 선택적 반례 검토자로만 둔다(adapter judge-only 유지). 결함 diff·수리 diff 각 2회 static 확인만 한다.
- **모델 교체:** Fable 5.2+는 출시 이름만 보고 자동 치환하지 않는다. 같은 역할로 다시 확인한다.
- **순서:** D1 재실행은 없다. arm·구성 순서를 교차 배치한다.

### 실행 수

| 단계 | 구성 | 실행 |
|---|---|---:|
| 상시 지침 스크린 | drift-bait 6 probe × N=4 × {opus-5.5, sonnet-5, astra, sol} × {current, slim} = 192. none은 N=2 참고 대조군(판정식 제외) = 48. EQ3 4과제(사전 고정) × 1 × 4모델 × 3변형 = 48 | 288(짧은 자동 실행) |
| 구조 스크린 | 0185(노출 회귀) + D4(등록 개발 자료, holdout 아님) × {A, B′, C, F} × 주 구성 2 | 16 |
| Grok static | 결함/수리 diff × 2 | 4 |
| 미노출 확인 | (새 어려운 2 × 2회 + 일상 1 × 1회) × 4 arm × 주 구성 2 | 40 (B′ 탈락 시 30) |
| 경량 확인 | 일상 2 × {native, 채택 후보} × {sonnet-5, sol} | 8 |

- 288회 지침 스크린은 선별이다. slim은 후보로 동결하고, 제품 반영은 S8에서 한다. managed text는 intent 전환 때 어차피 다시 쓰이므로, 사용자가 지침 이행을 두 번 겪지 않게 한다.
- B′가 살아 있으면 C도 확인까지 유지한다. B′·C 모두 신호가 없으면 확인·경량 단계 없이 종료한다.
- 실패를 지우는 재추첨은 없다. 공통 인프라 무효인 경우만 원인을 고친 뒤, 영향받은 비교 묶음을 원결과를 보존한 채 다시 실행한다.

### 채택 기준 (실행 전 등록, 결과를 본 뒤 변경 금지)

1. 허위 완료·범위 위반·신규 HIGH/CRITICAL은 채택을 막는다.
2. 대응 셀에서 A나 F가 완수한 요구를 후보가 잃으면, 해당 구성의 전면 교체를 승인하지 않는다.
3. **품질 경로:** 해당 구성의 어려운 확인 4회에서 native보다 최소 2회 더 완수해야 한다. 두 구성을 합산한 개선을 특정 구성의 근거로 쓰지 않는다.
4. **효율 경로:** 동일 요구 완수에서 F 대비 wall 또는 OUTPUT을 30% 이상 줄여야 한다. 다른 지표의 악화와 실패 소비는 함께 공개한다. OUTPUT 효율 경로를 통과한 후보는 시간만으로 탈락시키지 않는다.
5. **탈락:** 두 경로 모두 실패하고, 품질이 동률 이하이며, 후보/대조군 wall 비율이 1 이상이면 best-of-N 없이 탈락한다. 이는 NORTH-STAR:216 dominance rule의 적용 범위를 조정한 것이다.
6. B′가 C보다 필요한 이득을 보이지 못하면 C의 더 단순한 구조를 택한다. B′ 탈락만으로 C 채택을 정당화하지 않는다. 채택하는 후보는 native 품질 보존과 미노출 확인을 거쳐야 한다.
7. 근거가 부족하면 **교체 보류 또는 후보 종료**로 결론 낸다. "descriptive only라서 결정 불가"는 만들지 않는다.

### 확인 과제 작성 절차 (K-3)

1. 과제 선정 기준을 먼저 등록한다.
2. 후보·slim 지침·역할 설정·evaluator를 동결한다.
3. **후보 구현과 arm별 결과를 보지 않은 작성자**가 과제와 oracle을 만든다.
4. oracle은 reference/mutant 보정(0207 방식)을 통과해야 한다.
5. 0185와 D1–D4는 미노출 증거에 넣지 않는다.

## 5. 세션 계획

한 세션은 PR 하나로 끝나고 `complete --mode pr`로 전달한다. merge는 사용자가 하며, **앞 PR이 merge된 뒤** 다음 세션을 시작한다.

| # | 세션 | 산출물·완료 기준 | 하지 말 것 | packet |
|---|---|---|---|---|
| 0 | 계약 등록 (이 unit) | 이 문서, packet, HANDOFF, 포인터 갱신 | 제품 변경·모델 실행 | — |
| 1 | 설치 정리 + 전달 기본값 + 확인된 오탐 수리 | standards 4개: frontmatter 수정 + optional-skills로 이동. Claude 경로 reread 5문장 삭제(0099 K). pair-plan-schema를 benchmark로 이동. 전역 adaptive-thinking 신규 주입 중단(기존 값 보존). completion 기본 `pr`, auto는 명시적 opt-in. 기존 receipt mode 재사용과 소유 PR의 auto-merge 예약 처리 검증. spec-verify-check 연구 gate 오탐 수리(`:547`, `:1102`; T1b b3). mirror 동기화 | 없어질 resolve 본문의 어휘 정리 | T1a, T1b(c1,c2,b3,관련 lint,mirror) |
| 2 | 벤치 패키지 분리 | npm files에서 benchmark·repo-dev 스크립트 제거. `benchmark` 명령 삭제 + 직접 스크립트 이행 안내. README·lint 10e 갱신 | 벤치 기능 재설계 | T1b(a1–a5) |
| 3 | 실험 장치 v2 | 0210–0220 래퍼 체인을 한 디렉터리로 통합. 예산 기계 전부 삭제, watchdog·사후 사용량만 유지. native 수준 공통 계약. Claude/Codex owner·교차 reviewer·product-arm. F 설치 검증(tarball integrity·설치 manifest·실제 역할/pair 동작). D3.6·D2/D4 경로·pager 수정. 모델 없는 통제 + 스모크 | 새 범용 runner·상태 머신 | E1 |
| 4 | 상시 지침 스크린 | 계기 확장, 등록(EQ3 4과제·판정식·예측 선기록), 288회 실행, adjudicate 결과, slim 후보 동결 | 제품 지침 변경 | E2 |
| 5 | `/devlyn:intent` 후보 | 새 스킬 추가(기본값 불변). 커널·`--plan-only`·옵션 계약을 여기서 완성. 모델 없는 반례(stale PASS, 실패 exit, scope, 모델 불일치, 비소유 파일, 종료 실패). B′ 설치 경로 검증 | resolve 삭제·공유 helper 정리 | I1, I2(PR-A) |
| 6 | 구조 스크린 | 16회 + Grok static 4회. B′/C 계속·종료 판정 | 실패 재추첨, 노출 과제를 holdout으로 주장 | E1 장치 |
| 7 | 확인 + 채택 결정 | K-3 절차 → 40회(+경량 8회). 구성별 채택/보류/종료 결정과 기능·옵션 이행표 | 결과 후 기준·범위 변경, 미검증 모델로 일반화 | — |
| 8 | 제품 전환(다음 major) 또는 후보 종료 | **채택 시:** intent 기본, slim 지침, resolve/ideate 안내 전용, queue 위임, 설치 migration, 옛 task-completion 경로·재개 안내 보존. **탈락 시:** 후보 종료, full 유지, 그 뒤 연구 어휘 정리(T1b b1,b2,b4,b5) | 자동 merge·npm publish, 검증된 커널에 새 동작 추가 | I2(PR-B), T1b(b) |
| 9 | 호환 기간 종료 후 정리 | 한 major 뒤 안내 스킬 제거. 실제 참조가 사라진 helper만 삭제 | 참조가 남은 helper 삭제 | I2(PR-C), I1 |

## 6. 운영 규칙

- **인계:** 각 세션은 기준 SHA, 변경 범위, 실제 검사 결과, 미해결 항목, 다음 실행 명령, PR URL을 HANDOFF에 남긴다.
- **점검 시점:** 2영업일마다 그 실행 경로를 계속·축소·종료할지 결정한다. 충분한 검증을 일정 때문에 잘라내지 않는다.
- **독립 검토:** consequential 설계·등록에는 read-only 독립 검토 1회를 받는다. 추가 검토는 미해결 반례가 있을 때만 한다. 다라운드 freeze는 큰 발사에만 쓴다. 만장일치는 선행조건이 아니며 root가 결정한다.
- **resolve 호출:** arm F 외에는 resolve를 호출하지 않는다.

## 7. 대체와 보존

- **0201:** 진단은 유지한다. 다음 비교·채택 규정은 이 문서가 대체한다: rule 5, 24+48 bar, 재설계 1회, "full 유지 기본".
- **0206–0220:** 결과는 역사 기록으로 보존한다.
  - 0219의 stop 판정은 유지한다.
  - 0220은 발사하지 않았다.
  - 두 실험의 예산·재개 지침은 이 문서 §4가 대체한다.
  - 0204 owner·0206 과제·0207 evaluator·0208 계측·0210 이하 장치는 S3에서 재사용 원천이다.
- **동결 유지:** A16, 동결 결과, 원 WIP는 그대로 둔다.

## 8. 남은 사용자 확인

- **옛 이름 처리:** 옛 이름이 intent를 자동 실행하는 실행 alias vs 안내 전용. 기본값은 **안내 전용**이다(Astra·Opus 합의). 근거: 공유 스킬(`bin/devlyn.js:65`)과 프로젝트 지침(`bin/instructions.js:171`)의 갱신 시차는 옛 경로를 남길 근거일 뿐, 새 의미로 자동 실행할 근거는 아니다.
