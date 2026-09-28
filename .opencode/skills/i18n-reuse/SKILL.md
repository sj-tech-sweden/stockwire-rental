---
name: i18n-reuse
description: Use ONLY when adding, renaming, or editing Vue I18n translation keys in frontend/src/i18n (locales/en.js, locales/sv.js, prefillContent.js) or referencing translations in .vue/.js files. Enforces searching for an existing key before creating a new one, prevents duplicate keys within the same object literal, and keeps en/sv in sync. Trigger on phrases like "add translation", "new i18n key", "add a string", "translate this", "localize", or any edit to the i18n locale files.
---

# i18n reuse — search before you add

Stockwire Rental already has thousands of translation keys across `en.js`, `sv.js`,
and `prefillContent.js`. Adding a new key when a suitable one exists duplicates
effort, drifts the two locale files apart, and (worst case) silently overwrites an
existing key because **duplicate keys in the same object literal do not error — the
last one wins**. This bit us before: `reports.noLetterhead` was defined twice, the
second overwrote the first, and the GitHub code-quality bot flagged an "Overwritten
property" error.

## Workflow — do this BEFORE adding any key

1. **Identify the domain/namespace.** Keys are grouped by feature, e.g.
   `reports.*`, `inventory.products.*`, `app.actions.*`. Know which namespace your
   string belongs to before searching.

2. **Grep for an existing key by meaning, not just exact text.** A string you'd
   write as "No letterhead" might already exist as `noLetterheadUsed`
   ("No letterhead will be applied") or `noLetterheads` ("No letterheads
   configured..."). Search all locale sources:
   ```
   rg -n "<candidate words>" frontend/src/i18n/locales/en.js frontend/src/i18n/locales/sv.js frontend/src/i18n/prefillContent.js
   ```
   Also grep for the *key name* you intend to use (camelCase) to confirm it does
   not already exist anywhere.

3. **Reuse if semantically equivalent.** If an existing key conveys the same
   meaning, use it — even if the exact phrasing differs. Prefer reusing over
   adding.

4. **Only add a new key when nothing fits.** When you must add:
   - Place it in the correct namespace, near related keys, in **both** `en.js`
     and `sv.js` at the **same path**.
   - Use camelCase, descriptive, non-abbreviated keys
     (`reports.letterheadPdfOnly`, not `rep.lhPdf`).
   - Provide a **real Swedish translation** in `sv.js`. Never leave `sv` as
     English — that defeats the purpose and trips the code-quality bot.
   - Add `prefillContent.js` entries only when the string is template/prefill
     content, not a UI label.

5. **Guard against duplicate keys.** Before finishing, verify the key name appears
   **exactly once** per file. A second definition in the same object literal
   overwrites the first with no error. Grep the new key name across both locale
   files and confirm a single match each.

## Hard rules

- Never define the same key twice in one object literal.
- `en.js` and `sv.js` must stay structurally identical (same key paths).
- Never hardcode user-facing strings in `.vue`/`.js`; route them through `$t()` /
  `t()`.

## Reference

- Canonical structure and key conventions: `docs/I18N_GUIDE.md`.
- Repo-wide conventions (commit/branch style): `AGENTS.md`.
