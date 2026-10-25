1. **MEDIUM — [decide.py:85](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-clause-ablation/autoresearch/experiments/0258/decide.py:85): 아카이브된 시도의 scope 위반이 누락됩니다.** 계정 한도·Docker STOP은 scope 검사 전에 반환하므로 `scope_violations`가 없습니다. C가 범위 밖을 수정하고 중단된 뒤 재시도에 성공하면, 누락된 필드가 `False`로 처리되어 `C_UNSAFE`가 빠집니다. 재현 결과도 `scope:false`, `gaps:[]`였습니다. **수정:** 실행된 모든 보존 시도의 명시적 scope 판정을 요구하고, 없으면 `NOT_FINISHED`로 유지하십시오.

2. **MEDIUM — [d3-parseoptions-override.js:4](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-clause-ablation/autoresearch/experiments/0258/results/witnesses/d3-parseoptions-override.js:4): 동기 코드에는 10초 제한이 적용되지 않습니다.** `setTimeout`은 동기 `require()`·`parse()`를 중단하지 못하며 judge는 30초를 허용합니다. 10,200ms 지연 후 정상 반환하는 재현에서 unresolved 대신 **exit 0**이 나왔습니다. **수정:** 별도 프로세스 수준에서 10초 제한을 강제하고 시간 초과를 unresolved로 기록하십시오.

3. **MEDIUM — [judge.py:133](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-clause-ablation/autoresearch/experiments/0258/results/operator/judge.py:133): 비객체 JSON 출력은 probe 재시도를 건너뜁니다.** 마지막 stdout 줄이 `null`·배열·문자열이면 `.get()`이 예외를 발생시킵니다. `null` 재현은 **실행 1회, 결과 저장 0회**로 중단됐습니다. **수정:** dict 여부를 검증하고 잘못된 출력을 `unassessable`로 처리하여 등록된 한 번의 재시도를 수행하십시오.

4. **MEDIUM — [instructions.py:92](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-clause-ablation/autoresearch/experiments/0258/instructions.py:92): 중복 attachment 경로가 wrong-arm 검사를 통과합니다.** 한 attachment에 C의 `AGENTS.md` 다음 B의 `AGENTS.md`가 있으면 dictionary 변환이 앞의 내용을 버립니다. 재현에서 B 검사 결과는 위반 없음이었습니다. **수정:** 중복 경로를 거부하십시오. 현재 테스트는 설치 해시만 바꾸므로 실제 attachment의 누락·변조·wrong-arm·중복 사례도 추가해야 합니다.

5. **LOW — [decide.py:177](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0258-clause-ablation/autoresearch/experiments/0258/decide.py:177): prediction 3의 채점 조건이 명세보다 강합니다.** P2가 준비돼도 F10 verdict 하나가 없으면 `global_gaps` 때문에 prediction 3이 생략됩니다. 재현 결과는 `P2:true`, `predictions:{}`였습니다. **수정:** prediction 3은 명세대로 P2 readiness만으로 채점하십시오.

파일 변경은 없습니다. 쓰기 없는 테스트 **5개 통과**; 전체 pytest는 샌드박스의 임시 파일 생성 제한으로 수집 전에 중단됐습니다. 기존 네 D3 트리의 witness는 각각 두 번 실행하여 기대한 `[1,1]`, `[1,1]`, `[0,0]`, `[0,0]`을 확인했습니다.

VERDICT: REVISE
