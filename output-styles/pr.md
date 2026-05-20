# Pull Request Style

Format the response as a pull request body matching this project's PR discipline (`CLAUDE.md` — one PR = one `type(scope)` pair).

Begin with the title on its own line, as plain text, in the form:

`type(scope): imperative subject` — lowercase, no period, ≤ 70 characters. Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`. Breaking changes use `!` after the scope and add a `BREAKING CHANGE:` footer at the bottom of the body.

Then the body, using these section headings exactly, in this order:

## Summary

One to three bullets stating what changed. Every bullet must be consistent with the single `type(scope)` in the title. If two bullets describe different concerns ("adds X **and** refactors Y"), stop and flag — the branch is mixed and should be split per the `CLAUDE.md` PR Discipline section. Recommend the split rather than continuing.

## Why

The reasoning behind the change. Link to the issue, incident, RCA, or rule that motivated it. This section answers "why is this change correct *now*," not "what does the code do" — the diff covers what.

## Test plan

A bulleted checklist of how a reviewer verifies this locally. Each item is a concrete command or click-path, not a description. Examples:

- [ ] `go test ./...` — passes
- [ ] `make lint` — passes
- [ ] Open `/billing/portal` in a browser, confirm the cancel button is visible
- [ ] Run `gh pr checks` after push — all required checks green

## Rollback

One sentence: how to revert if this turns out wrong. If the answer is non-trivial ("would require a data migration"), say so plainly — that is itself reviewer-relevant.

---

If the change introduces a breaking change, add a final section:

## BREAKING CHANGE

One paragraph naming what breaks, who is affected, and the migration path.

Do not include sections that have no content. Do not pad with "N/A." If there is genuinely no rollback consideration (e.g. a docs-only change), write the rollback line as `Revert the commit.` and move on.
