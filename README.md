<div align="center">

# devlyn-cli

**A shared configuration toolkit for Claude Code — standardize AI-powered workflows across your team and projects.**

[![npm version](https://img.shields.io/npm/v/devlyn-cli.svg)](https://www.npmjs.com/package/devlyn-cli)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

</div>

---

## Why devlyn-cli?

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) is powerful out of the box, but teams need **consistent workflows** — shared commands, proven prompts, commit conventions, and reusable skills.

devlyn-cli installs a curated `.claude/` configuration into any project, giving your team:

- Battle-tested slash commands for debugging, code review, UI design, and more
- Reusable AI agent skills for investigation and prompt engineering
- Product and feature spec templates
- Commit message conventions

Zero dependencies. One command. Works with any project.

## Quick Start

```bash
npx devlyn-cli
```

That's it. The interactive installer walks you through the setup.

```bash
# Non-interactive mode (for CI/CD)
npx devlyn-cli -y

# Update to the latest config
npx devlyn-cli@latest

# List all available commands and templates
npx devlyn-cli list
```

## What Gets Installed

```
your-project/
├── .claude/
│   ├── commands/              # 9 slash commands
│   ├── skills/                # 3 reusable AI skills
│   ├── templates/             # Document templates
│   └── commit-conventions.md  # Commit message standards
└── CLAUDE.md                  # Project-level instructions
```

## Commands

Slash commands are invoked directly in Claude Code conversations (e.g., `/devlyn.resolve`).

| Command | Description |
|---|---|
| `/devlyn.resolve` | Systematic bug fixing with root-cause analysis and test-driven validation |
| `/devlyn.review` | Post-implementation code review — security, quality, best practices |
| `/devlyn.ui` | Generate 5 distinct UI style explorations from a spec or reference image |
| `/devlyn.feature-spec` | Transform product specs into implementable feature specifications |
| `/devlyn.product-spec` | Generate or incrementally update product spec documents |
| `/devlyn.discover-product` | Scan a codebase to generate feature-oriented product documentation |
| `/devlyn.recommend-features` | Prioritize top 5 features to build next based on value and readiness |
| `/devlyn.design-system` | Design system reference and guidance |
| `/devlyn.handoff` | Create structured handoff docs for context window transitions |

## Skills

Skills are triggered automatically based on conversation context.

| Skill | Description |
|---|---|
| `investigate` | Parallel code exploration with structured progress checkpoints |
| `prompt-engineering` | Claude prompt optimization based on Anthropic best practices |
| `feature-gap-analysis` | Identify missing features by comparing against baselines or competitors |

## Templates

| Template | Description |
|---|---|
| `template-product-spec.md` | Comprehensive product specification template |
| `template-feature.spec.md` | Feature specification template |
| `prompt-templates.md` | Reusable prompt snippets for common tasks |

## Optional Skill Packs

During installation, you can choose to add third-party skill packs:

```bash
# Vercel — React, Next.js, and React Native best practices
npx skills add vercel-labs/agent-skills

# Supabase — Supabase integration patterns
npx skills add supabase/agent-skills
```

## How It Works

1. Run `npx devlyn-cli` in your project
2. The CLI copies the config files into `.claude/`
3. Claude Code automatically reads `.claude/commands` and `.claude/skills`
4. Invoke commands like `/devlyn.resolve` in your Claude Code session

The installation is **idempotent** — run it again at any time to update to the latest config.

## Requirements

- Node.js 18+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI

## Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request.

1. Fork the repository
2. Create your branch (`git checkout -b feat/my-feature`)
3. Commit your changes following the included [commit conventions](config/commit-conventions.md)
4. Push to the branch (`git push origin feat/my-feature`)
5. Open a Pull Request

## License

[MIT](LICENSE) — Donut Studio

