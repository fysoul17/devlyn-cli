**FIX**

- **MEDIUM — [driver.py:264](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0257-amend-2/autoresearch/experiments/0257/driver.py:264)**: 기존 reserve 때문에 생긴 `split_wait`가 `--amend-caps` 이후에도 남습니다. 메모리 내 재현에서 caps=95/95, 두 창 사용량=60%인데도 리셋까지 대기했습니다. 문서대로 재시작해도 며칠을 낭비할 수 있으므로, amendment 등록 시 이전 reserve 대기를 해제해야 합니다.

- **MEDIUM — [amendment-2.md:19](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0257-amend-2/autoresearch/experiments/0257/amendment-2.md:19)**: 동일 임계값이 A/B 편향 부재를 보장하지는 않습니다. 94%에서 짧은 A는 완료하지만 긴 B는 quota fault 후 재실행될 수 있습니다. 폐기된 시도의 비용도 합산되므로 비용 판정에 영향을 줍니다. 계정·잔여량에 따른 교란 가능성을 명시하고, “Usage is descriptive”를 window utilization으로 한정해야 합니다.

그 외 95% 경계와 새 split-wait 동작은 확인했습니다. 정상 identity의 실행 quota fault는 보관·재실행되며, 완료 수에는 최종 verdict만 반영됩니다. 제거된 estimate/account-pair 검사는 판정 계산에 필요하지 않습니다.
