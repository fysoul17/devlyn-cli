# Commit Conventions

Use conventional commits: `<type>: <description>` (scope optional: `<type>(<scope>): <description>`)

| Type       | Use for                                              |
|------------|------------------------------------------------------|
| `feat`     | New feature                                          |
| `fix`      | Bug fix                                              |
| `chore`    | Routine tasks (deps, non-production changes)         |
| `docs`     | Documentation updates                                |
| `style`    | Code style only (formatting, spacing)                |
| `refactor` | Restructuring (no fix or feature)                    |
| `perf`     | Performance improvements                             |
| `test`     | Adding or updating tests                             |
| `build`    | Build system or dependency changes                   |
| `ci`       | CI/CD pipeline updates                               |
| `revert`   | Reverting a previous commit                          |
| `temp`     | Temporary changes (not for long-term merge)          |

## Examples

```
feat: add user authentication
fix: resolve null pointer in auth middleware
refactor(api): simplify request validation
docs: update API usage guide
chore: upgrade next.js to v16.2
```
