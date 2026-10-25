1. **MEDIUM — [judge.py:81](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-clause-ablation/autoresearch/experiments/0258/results/operator/judge.py:81): D3 전용 marker 검사가 일반 witness까지 거부합니다.** 기존 `d3-executable-delimiter.js`처럼 JSON을 출력하고 exit 1로 결함을 증명하는 witness도 두 실행 모두 exit 2로 바뀝니다. 모의 실행에서 `[2, 2]`, `unresolved`를 확인했습니다. 이 때문에 기존 severe-finding 판정 절차가 정상 재현을 인정하지 못합니다. **수정:** D3 marker 검사를 해당 witness로 한정하고, 일반 witness는 별도 실행 완료 marker로 기존 0/1 규약을 지원하십시오. 일반 witness 회귀 테스트도 필요합니다.

2. **MEDIUM — [decide.py:186](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-clause-ablation/autoresearch/experiments/0258/decide.py:186): `NOT_FINISHED`에서도 JSON에 p-value가 공개됩니다.** 필수 판단이 누락된 8 대 0 fixture에서 token은 `NOT_FINISHED`지만, `tests`에는 raw `0.00122358`, adjusted `0.00244716`, `rejected: true`가 남습니다. `main()`은 이를 저장·출력하므로 frozen DESIGN의 “No p-value is emitted”를 위반합니다. **수정:** prediction용 내부 계산은 유지하되 `NOT_FINISHED`에서는 공개되는 `tests` 값을 비우고 이를 테스트하십시오.

쓰기 없는 테스트 6개 통과. 기존 네 트리의 witness 결과는 각각 `[1,1] / [1,1] / [0,0] / [0,0]`이며 marker도 일치했습니다. 전체 pytest는 샌드박스의 임시 파일 생성 제한으로 수집 전에 중단됐습니다. 파일 변경은 없습니다.

VERDICT: REVISE
