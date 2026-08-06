# Claude Configuration Learnings

This file documents lessons learned about what makes Claude rules, skills, hooks, and agents work reliably. It is updated automatically as new insights are discovered during working sessions.

---

## Rule Authoring

### Use mandatory language, not advisory language

Rules using "suggest", "consider", or "prefer" drift across sessions. Claude interprets soft language as optional and skips it without consequence. Use "always", "must", "never", and "do not" for behaviors you want to be consistent.

**Pattern that drifts:**
> Consider running `/review` before shipping.

**Pattern that holds:**
> Always recommend `/review` before shipping. Do not skip this recommendation.

---

### Add a "don't revert" anchor with the reasoning

Rules that say what to do but not why it's non-negotiable get quietly reversed when Claude encounters complexity or time pressure. A single sentence explaining the intent prevents this.

**Without anchor (reverts):**
> Dependency injection via constructor functions — pass dependencies in, never use globals.

**With anchor (holds):**
> Dependency injection via constructor functions — pass dependencies in, never use globals.
> **This is an intentional design decision — do not simplify it away.** When code grows complex, the correct response is to refactor, not to revert to globals or singletons.

---

### Define exceptions explicitly with examples, not categories

Vague exception categories like "purely mechanical changes" are interpreted too broadly across sessions. Exceptions should be defined with literal examples so there is no room for interpretation drift.

**Too broad (overused):**
> Exceptions: purely mechanical changes.

**Scoped correctly (stable):**
> Exceptions: renaming an identifier, moving a file to a different package, updating an import path. If there is any change to logic, control flow, or observable behavior, it is not mechanical.

---

### Resolve contradictions between rules and skills

When a rule and a skill cover the same behavior but say different things, Claude alternates between them depending on which file is loaded first. Every contradiction creates a cycle.

**Known example (now resolved):** `rules/tdd.md` said `/refactor` was a TDD exception; `skills/refactor/SKILL.md` required characterization tests first. These said opposite things. Fix: align them to one answer — refactor requires characterization tests, which is a different test-first process, not an exception.

---

### Align rule scope with skill scope

If a rule suggests a skill for a narrow task (e.g., a single deprecated pattern in the current file) but the skill is written to scan the entire codebase, the mismatch creates confusion. Either give the skill a scoped mode or make the rule match the skill's actual behavior.

**Example (now resolved):** `rules/migrate-suggest.md` suggested `/migrate` for individual deprecated patterns mid-task, but `skills/migrate/SKILL.md` opened a full codebase scan. Fix: added file-level vs codebase-level modes to the skill.

---

### Two files that point at each other as source of truth guarantee drift

When file A says "the full X is in file B" and file B says "the full X is in file A", neither is authoritative and both grow overlapping content that drifts apart. Consolidate into one file; the other becomes a one-line pointer.

**Known example (now resolved):** `skills/CLAUDE.md` said `rules/skill-conventions.md` was authoritative; `rules/skill-conventions.md` said `skills/CLAUDE.md` was authoritative. Frontmatter, structure, language, and invocation-control sections appeared in both with different depth. Fix (PR #70): consolidated authoring content into `rules/skill-conventions.md`; `skills/CLAUDE.md` became a 5-line pointer.

---

### paths glob must match the files where the rule actually applies

A rule with a `paths` glob whose body starts with "ignore this rule unless…" loads and self-cancels on every non-matching file — wasting context on every trigger. The `paths` glob is the enforcement mechanism; do not double-check inside the body. If the body has to filter, the glob is wrong.

**Known example (now resolved):** `rules/readme-standard.md` had `paths: ["**/README.md"]` (matches every README at any depth) but its first paragraph said "This rule applies only to the `README.md` at the repository root." 6 of 7 READMEs in this repo triggered the rule only to be told to ignore it. Fix (PR #71): `paths` changed to `README.md` (bare = repo-root anchored, matching the `go.work` convention in `rules/go-workspace.md`).

---

### Do not paraphrase a referenced rule inside CLAUDE.md

CLAUDE.md is always-loaded every session. If a rule is both paragraph-summarized in CLAUDE.md **and** linked to its file, both load into context and hold identical content twice. Replace the paraphrase with a one-line pointer plus the trigger signals only — the rule body owns the tables.

**Known example (now resolved):** CLAUDE.md had ~1,200 tokens across 6 rule sections (algorithmic-complexity, defensive-assertions, lint-suppression, black-box-testing, mutation-testing, tool-language-selection) that both paraphrased content **and** linked to the rule files. Fix (PR #68): collapsed to one-line pointers with trigger signals; CLAUDE.md 14.4 KB → 7.6 KB.

---

### Stapling secondary guidance onto the wrong file trigger fires nowhere useful

If rule R has `paths: ["A.md"]` but half its body is about maintaining `B.md`, that half fires on every A.md edit (unnecessary weight) and never fires on B.md edits (missing when needed). Split the concerns into two rules with matching `paths`.

**Known example (now resolved):** `rules/readme-standard.md` had 50 lines about how to maintain `LEARNINGS.md` — but the `paths` glob only matched README.md. Learnings guidance loaded on README edits (waste) and never on LEARNINGS.md edits (silent gap). Fix (PR #71): extracted to `rules/learnings-standard.md` with `paths: ["LEARNINGS.md"]`.

---

### When editing YAML frontmatter, `Read` to the closing `---` — not an arbitrary line count

`Edit`'s `old_string` must be complete for the replacement to be complete. If the initial `Read` used `limit: N` and `N` fell inside the frontmatter block, the caller sees only part of the frontmatter and any `Edit` built from that Read leaves the rest untouched — including entries the caller believed were removed. The correct Read target is the closing `---` delimiter, not a line count.

**Known example (now resolved):** PR #74 claimed to remove the `paths` block from `rules/owasp-top-10.md`. The initial `Read(limit: 15)` only surfaced the description + first 12 language globs, so the Edit deleted those 12 lines but left 13 more (`.c`, `.cpp`, `.h`, `.hpp`, `.php`, `.sh`, `.bash`, `.zsh`, `.sql`, `.tf`, `Dockerfile*`, `docker-compose*.y*ml`, `.github/workflows/*.y*ml`) in place — the rule still auto-loaded on every C/C++/PHP/shell/SQL/Terraform/Docker/GH-workflow edit. Discovered by audit pass 3; fixed in PR #78.

**Rule of thumb:** for any YAML frontmatter Edit, either `Read` the file with no `limit`, or use `Read` with a limit large enough that the closing `---` appears in the output. If the closing `---` isn't in your Read output, do not Edit — read more first.

---

### Automated frontmatter parsers must anchor to file start, not naïvely split on `---`

Markdown bodies often use `---` as a horizontal rule (thematic break) between sections. A script that separates frontmatter from body with `text.split("---", 2)` silently mis-detects the first two body-level HRs as frontmatter delimiters, then inserts or edits "frontmatter" content in the middle of the body — corrupting the file.

The correct pattern is an anchored regex that matches only at file start and requires a proper closing delimiter:

```python
import re
FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
m = FRONTMATTER.match(text)
if m:
    fm_body = m.group(1)
    rest = text[m.end():]
    # ... safely edit fm_body, then reassemble as: f"---\n{new_fm_body}\n---\n{rest}"
else:
    # File has no frontmatter — prepend a fresh one, don't try to split
    text = f"---\n{new_fm_body}\n---\n\n{text}"
```

**Known example (now resolved):** the first attempt of PR #79 (add `description` to 26 rules) used naive `split("---", 2)` and corrupted 10 rule files — e.g. `docs-principles.md` has 6 body-level `---` HRs; the split treated one as a frontmatter delimiter and stuffed the new description into the middle of the doc while dropping the closing `---`. Reverted with `git checkout rules/` and rewrote using the anchored regex above; second attempt landed cleanly.

Applies to any script that reads or edits frontmatter across many files — audit tooling, migration scripts, batch renames.

---

### Large reference rules should not have broad `paths` globs

A rule whose own opening line describes it as "a recognition list, not an implementation guide" is reference material — it should be consulted deliberately by reviewer agents, not auto-loaded on every code edit. Broad language-extension globs (`**/*.go`, `**/*.py`, etc.) on rules >150 lines are a per-edit token drain most edits never benefit from.

**Known example (now resolved):** `rules/owasp-top-10.md` (303 lines / 20.8 KB) auto-loaded on every code edit in 12 language extensions. The rule's own preamble explicitly framed it as reference. Most edits don't touch a trust boundary, so 90% of loads were dead weight. Fix (PR #74): removed the `paths` glob entirely; extended each language reviewer agent's Standards-reference line to load `owasp-top-10.md` on demand when the code under review touches auth, input parsing, deserialization, secrets, or network I/O. `rest-reviewer` treats OWASP as always-load since HTTP endpoints are trust boundaries by default.

**Rule of thumb:** rules over ~150 lines with `**/*.<lang>`-shaped globs deserve scrutiny. Either narrow the glob to the actual scope (see next entry) or remove it entirely and route through a reviewer agent.

---

### Narrow `paths` globs to actual scope, not lowest-common-denominator language extension

A rule that applies only to a specific code pattern (HTTP handlers, database migrations, etc.) should not glob on the language extension — it forces the rule to load on every file in the language even when the pattern is absent. Narrow to directory or filename conventions the pattern actually lives in.

**Known example (now resolved):** `rules/rest-api-conventions.md` (120 lines) had `paths: ["**/*.go", "**/*.py", "**/*.ts", "**/*.js"]` — fired on every language file even though 90% aren't REST handlers. Fix (PR #74): narrowed to `["**/handlers/**", "**/routes/**", "**/api/**", "**/controllers/**", "**/endpoints/**"]`. For code outside those paths, the `rest-reviewer` agent loads the rule on demand when reviewing endpoint code.

---

## Skill Structure

### Level 2 SKILL.md body persists in session context after invocation

Every line in the body of a `SKILL.md` loads into context on invocation AND persists for the rest of the session — not just the current task. A 500-line dispatcher that inlines every subcommand means `/git sync` (a rebase) pays for the full `/git reviewer` parallel-fanout prose it will never execute. Extract per-subcommand dispatchers into Level 3 files the workflow reads only when that subcommand fires.

**Known example (now resolved):** `skills/git/SKILL.md` (465 lines) and `skills/docs/SKILL.md` (454 lines) inlined every subcommand. Fix (PR #69): extracted per-subcommand dispatchers to sibling files (`ship.md`, `reviewer.md`, `merge.md`, `write.md`, `review.md`, `research.md`); `SKILL.md` files dropped to 201 and 56 lines. Per-subcommand invocations dropped 36-88%.

---

### Project-level CLAUDE.md files load on every file under the directory

`skills/CLAUDE.md` (a project-level `CLAUDE.md`) loads whenever the active file lives anywhere under `skills/` — including Level 3 files like `ship.md`, `review.md`, and Level 3 scripts. Content targeted at only SKILL.md authoring is dead weight on every Level 3 edit. Keep the project CLAUDE.md tiny (a pointer); put authoring conventions in a rule whose `paths` glob only matches SKILL.md.

**Known example (now resolved):** editing a newly-extracted Level 3 file loaded the full 195-line `skills/CLAUDE.md`. Fix (PR #70): consolidated authoring content into `rules/skill-conventions.md` (`paths: ["skills/*/SKILL.md"]`); `skills/CLAUDE.md` became 5 lines. Level 3 edits load 5 lines instead of 195 (-97%).

---

### After consolidating N skills into one dispatcher, sweep vestigial "Replicates the prior /X" prose

When a family of skills is merged into one dispatcher (e.g. `/go-docs`, `/py-docs`, `/nvim-docs`, `/gherkin-docs` → `/docs write`), the natural first cut labels each subcommand with "Replicates the prior `/X` skill." The `aliases:` frontmatter already handles historical invocation attribution — the prose in the body serves no ongoing purpose and pays 1-2 lines per subcommand on every invocation.

**Known example (now resolved):** 12 "Replicates the prior /X skill" sentences remained across `skills/code/SKILL.md`, `skills/git/SKILL.md`, `skills/docs/write.md` months after the underlying consolidations. Fix (PR #74): removed via python regex — single-sentence lines deleted entirely; multi-sentence lines had just the prefix stripped, preserving the substantive follow-on context.

**Rule of thumb:** the aliases: frontmatter is the discovery mechanism; body prose is not. After a consolidation, grep for `"Replicates the prior"` and remove.

---

## Hooks

### Extract JSON fields with bash regex before spawning jq

Hooks that fire on every tool call typically extract a value from the harness's JSON payload with `jq -r '.tool_input.field // empty'`. On macOS jq startup is ~10-15 ms per spawn — for a session with 30-50 tool calls, hundreds of milliseconds of blocking hook latency for a value bash can extract natively. Use `[[ $INPUT =~ \"field\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]]` and fall back to jq only when the regex misses (embedded quotes). Applied in PRs #68 and #70 across `sensitive-file-warn.sh`, `tdd-remind.sh`, `conflict-check.sh`, `secret-scan.sh`, `lint.sh`.

---

### Debounce lint hooks that fire per-Edit on multi-Edit bursts

`hooks/lint.sh` fires on every PostToolUse Edit/Write. A common pattern — 5-10 sequential Edits to the same file in one message — triggers 5-10 lint runs that see nearly-identical file state. On slow linters (Go modules, complex ruff configs), this adds seconds per burst. Debounce per-file via a `$TMPDIR/claude-lint-$USER/<file>.ts` timestamp: on entry, skip if the same file was linted within 2 s. Applied in PR #68.

---

### Rate-limit hooks that run network commands, and background them

Any hook that invokes `git fetch`, `curl`, or similar network commands should not run synchronously on every trigger — the round-trip adds visible seconds to every user action on slow networks. Store the last-run timestamp per repo (`$GIT_DIR/*.ts`), skip if within N seconds (300 s / 5 min is a good balance), and background the actual command with a short cap (2 s) so slow networks never block the user path. Surface warnings only on refreshed data. Applied in PR #68 for `hooks/conflict-check.sh`.

---

### Matcher-narrow hooks with combined grep alternation before per-pattern greps

`hooks/secret-scan.sh` originally ran 6 sequential `grep -qE` calls unconditionally on every prompt submit to check for 6 different secret patterns. 6 subprocess spawns per prompt for the 99% of prompts that contain no secrets. Combine the patterns into one alternation grep as a reject filter (`grep -qE 'sk-...|gh[poas]_...|AKIA...'`); only if that hits, run the per-pattern greps to label which one matched. Applied in PR #68.

---

### Pre-normalize files under a PostToolUse formatter — otherwise per-file Edits leak a whole-file reformat into every commit

The PostToolUse `ruff format` hook reformats any file it touches to match the project's style. On a file that doesn't already match, a small Edit produces a diff of *every* non-conforming block plus the intended change — in PR #82, a 4-line-per-file shebang change across 14 `scripts/*.py` files ballooned to 1018 insertions / 203 deletions because every wide dict literal got wrapped in the same commit. Fix: when a formatter hook is added (or a file has drifted from its config), run the formatter once across the affected set as a standalone `style(scope): reformat` PR *before* the first content edit. Every subsequent Edit then produces a clean +N/-N diff and can't couple "one commit, two concerns."

---

### Add-import + first-use must land in one Edit — ruff `--fix` strips the import between two Edits

`hooks/lint.sh` runs `ruff check --fix` after every Edit/Write. Between Edit #1 (adds `import X`) and Edit #2 (adds the first `X.foo` reference) — even inside the same message — ruff sees `X` imported but not used and autoremoves it. Edit #2 then lands against a file where `import X` no longer exists; the script raises `NameError: name 'X' is not defined` at runtime. Hit in PR #89 when `import argparse` was added ahead of an `argparse.BooleanOptionalAction` usage. Fix: fold the import and its first usage into a **single** Edit `new_string` so ruff sees the pair together, or Read the file between the two Edits to verify the import survived before firing the next one.

---

## TDD Enforcement

### "Invoke the skill" is not the same as "follow the cycle"

A rule that says "invoke `/test-driven-development`" only loads the instructions. Claude can acknowledge the skill and still skip the RED step. The rule must mandate specific observable outputs: write the test, run it, show the failure output, then implement.

---

### The hook reminds; it does not block

The `tdd-remind.sh` PreToolUse hook fires before editing production files and outputs a warning. It exits 0 (allows the edit), so it cannot enforce TDD on its own. Its value is in the language weight of the message — "STOP / do not proceed" carries more force than "confirm". The hook and the rule together create the behavior; neither alone is sufficient.

---

### Refactor is not a TDD exception — it is a different test-first process

The red-green-refactor cycle (new failing test → minimal implementation) does not apply to refactoring. But tests are still required first. Characterization tests that document current behavior must exist before touching any code. Calling refactor a "TDD exception" without this nuance causes Claude to skip tests entirely when refactoring.

---

## Go-Specific

### Go workspace repos require per-module command iteration

In a Go workspace (`go.work` present), `go test ./...` and `golangci-lint run ./...` from the repository root fail with "directory prefix . does not contain modules listed in go.work". Every toolchain command must iterate over `go.mod` files using `find . -name "go.mod" | while read f; do (cd "$(dirname "$f")" && <cmd>) || exit 1; done`. If the project has a Taskfile, prefer `task lint` / `task test` — they already encode the correct pattern.

---

### golangci-lint major version must match the module's Go version

golangci-lint is compiled with a specific Go version. If a module declares `go 1.26` but golangci-lint was built with Go 1.24 (v1.x), it fails with "file requires newer Go version go1.26 (application built with go1.24)". Use `golangci-lint v2.x` for modules declaring `go 1.26`. In GitHub Actions, `golangci-lint-action@v9` resolves to v2.x; `golangci-lint-action@v6` caps at v1.64.8 (Go 1.24) and will fail.

---

### golangci-lint v2 requires `version: "2"` in `.golangci.yml`

golangci-lint v2 rejects v1 config files silently or with "unsupported version of the configuration". The v2 format requires `version: "2"` at the top, moves formatter config to a top-level `formatters` section, moves linter settings to `linters.settings`, and moves exclusion rules to `linters.exclusions.rules`. `gosimple` is merged into `staticcheck` in v2 — listing it separately causes an error.

---

### All `go.mod` files in a workspace must declare the same Go version

When Go stdlib files gain build constraints (e.g., `//go:build go1.26` on FIPS files), modules that declare an older version exclude those files at compile time, causing `undefined` errors at runtime. After upgrading `go.work` to a new Go version, update every `go.mod` in the workspace to match, then run `go work sync`.

---

### Falling back to `go vet` on golangci-lint version mismatch creates false security

When golangci-lint can't run due to a Go version mismatch, falling back to `go vet` feels safe but isn't. `go vet` only catches compilation-level issues; it misses godot (missing periods), goimports (import grouping), gocyclo (complexity), and every style linter. The result is that lint looks "clean" locally while CI fails. The correct response to a version mismatch is a **hard error** with a clear fix: `go install golangci-lint/v2/... @latest` or `task deps`. Do not silently downgrade.

---

### Per-repo `tool` directives in `go.mod` eliminate cross-repo lint version drift

When working across Go repos pinned to different `go.mod` versions, a single global `golangci-lint` cannot satisfy them all — the binary's build-Go must be ≥ every repo's declared Go version, and the next Go SDK bump re-creates the mismatch. Go 1.24's `tool` directive solves this structurally: each repo runs `go get -tool github.com/golangci/golangci-lint/v2/cmd/golangci-lint@latest` once to pin its lint version in `go.mod`, and lint orchestrators (the `hooks/lint.sh` Go branch, CI) prefer `go tool golangci-lint run ./<pkg>` over the global binary. The tool is rebuilt against the local Go SDK on every invocation, so version mismatch is impossible by construction. Dispatch order in `hooks/lint.sh`: (1) `go tool golangci-lint` if `go.mod` declares it, (2) `task lint` if `Taskfile.yml` defines it, (3) global `golangci-lint` with the version check, (4) `go vet` with warning.

---

### Pre-push hooks prevent CI-only lint failures

A `.githooks/pre-push` script that runs `golangci-lint run ./...` per module blocks the push before it reaches CI. Without this, any lint issue — regardless of how obvious — must wait for a CI run to be discovered. Add `task hooks` to configure it in one step, and document in the README.

---

### `fail-fast: true` on matrix lint jobs cascades into false failures

In a GitHub Actions matrix job for per-module linting, the default `fail-fast: true` cancels all remaining jobs when one fails. This hides failures in other modules and makes CI output misleading. Set `fail-fast: false` on lint matrix jobs so every module's result is always reported independently.

---

### `go test -race` belongs in the review linter step, not just the checklist

The `go-reviewer` agent checklist had "Race detector passing: `go test -race`" as an item to check, but nothing actually ran it. Adding it to the review skill's linter step (`go vet ./... && go test -race ./...`) makes it a blocking Must Fix finding rather than an advisory note.

---

### Benchmarks should be flagged as missing, not run automatically

Running `go test -bench=./...` on every review is too slow and only measures what has already been benchmarked. The right behavior is: flag missing benchmarks as a Suggestion-level finding when code is on a hot path, processes large inputs, or is latency-sensitive. Use `/go-bench` explicitly when you want to measure.

---

## Python-Specific

### semantic-release build_command: run `uv lock` before `uv run`

semantic-release bumps `pyproject.toml` first, then runs `build_command`. If `build_command` starts with `uv run ... && uv lock`, the `uv run` may fail against the stale lockfile and — due to `&&` short-circuit — `uv lock` never executes. The stale lockfile is committed alongside the version bump and breaks `uv sync --locked` on the *next* CI trigger, one merge later. Always order it `uv lock && uv run ...`.

---

## Complexity

### Cyclomatic complexity limit should be ≤ 7 globally

A limit of 10 is too permissive — functions with complexity 8–10 are measurably harder to test and reason about. The limit of 7 applies to Go, Python, and Lua. Gherkin is declarative and does not have cyclomatic complexity.

---

## Setup & Configuration

### LSP plugins should be configured per-project, not globally

Enabling `gopls-lsp`, `pyright-lsp`, and `lua-lsp` in the global `~/.claude/settings.json` starts all three language servers on every session regardless of the project type. Move them to a per-project `.claude/settings.json` at the repo root, enabling only the languages that project uses.

**Template for a Go project:**
```json
{
  "enabledPlugins": {
    "gopls-lsp@claude-plugins-official": true
  }
}
```

**Available plugins:** `gopls-lsp@claude-plugins-official`, `pyright-lsp@claude-plugins-official`, `lua-lsp@claude-plugins-official`

---

### `settings.json`: a `Bash(*)` wildcard shadows every `Bash(x:*)` allow entry

If `settings.json` `permissions.allow` contains the `Bash(*)` wildcard, every specific `Bash(x:*)` entry below it (`Bash(awk:*)`, `Bash(git:*)`, …) is redundant — the wildcard already permits them all. The specific list is not enforced; it is decorative.

Two valid stances:

- **Concise:** keep only `Bash(*)` and let it stand alone. Small settings.json, one line of intent.
- **Defense-in-depth:** remove `Bash(*)` and keep the specific allowlist as the only permission surface. Larger settings.json, tighter effective scope.

Do not do both — the combination is pure clutter and misleads a reader trying to understand what's actually approved.

**Known example (now resolved):** `settings.json` had `Bash(*)` plus 94 specific `Bash(x:*)` entries. Fix (PR #76): removed the 94 specifics, kept the wildcard. Effective permission set unchanged; -94 lines from the file. If the wildcard is ever tightened, `git log -p settings.json` shows the removed list for reference.

**Detector for future audits:** any `settings.json` with both a wildcard tool permission (`Bash(*)`, `Read(**)`, `Edit(**)`, `Write(**)`, `mcp__*`) AND narrower entries of the same tool — flag as redundant, ask which stance the owner wants.

---

## Concurrency (Go)

### Key patterns that prevent goroutine leaks

- Every generator must have a done/quit signal — a producer blocked on send with no consumer leaks forever
- Scatter-gather channels must be buffered to the number of senders — unbuffered channels leak abandoned goroutines when a timeout fires
- `close()` on a channel while goroutines are still sending to it panics — signal them to stop first
- `time.After` called inside a loop creates a new timer each iteration; a global deadline never triggers — call it once outside the loop

---

## Planning Prompts

Reusable prompts for common Claude Code workflows.

### Discovery before building

Use this before starting any non-trivial feature to align on problem, audience, and scope before writing code:

> Before we start building, interview me about this:
>
> What is the core problem this solves?
> Who is this for? What does success look like? What should this NOT do?
>
> Summarize it back to me before we write any code.
