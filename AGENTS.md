# AGENTS.md — How to work in this repository

Guidance for AI assistants (and humans) contributing to Stockwire Rental. Follow
these conventions so contributions stay consistent and reviewable.

## Repository at a glance

- **Stack:** Vue 3 + Quasar frontend (`frontend/`), FastAPI backend (`backend/`).
- **i18n:** Vue I18n with English (`en`) and Swedish (`sv`). Locale files live in
  `frontend/src/i18n/locales/{en,sv}.js` plus `frontend/src/i18n/prefillContent.js`.
- **Tooling:** Renovate for dependency updates, ruff for Python lint, GitHub
  code-quality bot on PRs.

## Commit messages

Use **Conventional Commits**. This matches the existing history
(`feat(...)`, `fix(...)`) and lets tooling and release notes parse changes.

```
<type>(<scope>): <subject>
```

- **type** (one of): `feat`, `fix`, `docs`, `style`, `refactor`, `perf`,
  `test`, `build`, `ci`, `chore`.
- **scope**: short module/area, e.g. `reports`, `i18n`, `auth`, `inventory`,
  `jobs`, `settings`. Omit only when the change truly spans everything.
- **subject**: lowercase, imperative ("add", "fix", "remove"), no trailing
  period, no issue number (use the PR body).
- Append `!` after the scope for breaking changes, e.g. `refactor(api)!: ...`.

Good:
```
feat(reports): add letterhead preview to report designer
fix(i18n): reuse existing noLetterhead key instead of duplicating it
chore(deps): bump ruff to v0.16.9
```

Bad:
```
fixed stuff
Update
feat(Better report generation)   # missing colon + lowercase subject convention
```

Do **not** commit unless the user explicitly asks. When asked, write the commit
message in this format and keep the diff focused on the requested change.

## Branch naming

Name branches with the same `type/` prefix as the commit type, kebab-cased:

```
feat/report-generation-from-dialogs
fix/letterhead-duplicate-key
chore/llm-coding-guidance
```

Existing loose branch names (`Better-products`, `Fix-frontend`) predate this
convention; prefer the `type/...` form for new work.

## Internationalization (i18n)

**Reuse existing terms before creating new ones.** Full rules live in
`.opencode/skills/i18n-reuse/SKILL.md` (auto-triggers when you touch locale
files) and `docs/I18N_GUIDE.md`. The non-negotiables:

1. Before adding a key, grep `frontend/src/i18n/locales/{en,sv}.js` and
   `prefillContent.js` for a semantically equivalent existing key. Reuse it.
2. Never add a key that already exists in the same object literal — duplicate
   keys silently overwrite each other and trip the code-quality bot (this is how
   `noLetterhead` was overwritten).
3. Keep `en.js` and `sv.js` structurally identical: any new key goes in both,
   at the same path, with a real translation (never leave `sv` as English).
4. Use camelCase, descriptive, domain-grouped keys (`reports.letterheadPdfOnly`),
   not abbreviations.

## General

- Match existing code style and frameworks; don't introduce new libraries
  without checking the codebase already uses them.
- Don't hardcode user-facing strings — route them through i18n.
- Run the project's lint/typecheck (ruff for backend, project linter for
  frontend) before considering a change done.
