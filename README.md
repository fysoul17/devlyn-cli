# devlyn-cli

Claude Code 설정을 팀과 프로젝트 간에 공유하는 CLI 도구.

## 사용법

```bash
# 새 프로젝트에 .claude 설정 설치
npx devlyn-cli

# 프롬프트 없이 설치 (CI용)
npx devlyn-cli -y

# 최신 버전으로 업데이트
npx devlyn-cli@latest
```

## 포함된 Core Config

- **commands/** - 커스텀 슬래시 커맨드 (devlyn.ui, devlyn.review 등)
- **skills/** - AI 에이전트 스킬 (investigate, prompt-engineering 등)
- **templates/** - 코드 템플릿
- **commit-conventions.md** - 커밋 메시지 컨벤션

## Optional Skill Packs

설치 시 선택하거나, 나중에 수동 설치:

```bash
# Vercel - React, Next.js, React Native best practices
npx skills add vercel-labs/agent-skills

# Supabase - Supabase integration patterns
npx skills add supabase/agent-skills
```

## 업데이트

새 버전이 배포되면:

```bash
npx devlyn-cli@latest
```
