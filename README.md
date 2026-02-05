# devlyn-cli

Claude Code 설정을 팀과 프로젝트 간에 공유하는 CLI 도구.

## 사용법

```bash
# 새 프로젝트에 .claude 설정 설치
npx devlyn-cli

# 최신 버전으로 업데이트 (동일한 명령어)
npx devlyn-cli
```

## 포함된 설정

- **commands/** - 커스텀 슬래시 커맨드
- **skills/** - AI 에이전트 스킬
- **templates/** - 코드 템플릿
- **commit-conventions.md** - 커밋 메시지 컨벤션

## 설치 후

프로젝트의 `.claude/` 폴더에 설정이 복사됩니다. 이 폴더를 `.gitignore`에 추가하거나, 팀과 공유하려면 git에 커밋하세요.

## 업데이트

새 버전이 배포되면:

```bash
npx devlyn-cli@latest
```
