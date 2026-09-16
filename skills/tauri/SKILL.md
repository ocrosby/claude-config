---
description: Use when the user asks for a new desktop app, wants to add Tauri to an existing frontend, needs Tauri toolchain/dependency setup, or wants to design/review/debug a Tauri v2 app. Invoke as /tauri <new|setup|design|add-plugin|build|review|debug>.
argument-hint: "<subcommand> [arguments]"
arguments: [subcommand]
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# Tauri: Desktop App Dispatcher

Use this skill whenever a new desktop app is requested, or existing Tauri (v2) code needs designing, building, reviewing, or debugging. Delegates architecture to `tauri-architect`, review to `tauri-reviewer`, and debugging to `tauri-debugger`. Dependency installation is governed by `rules/tauri-setup.md`; project/security conventions by `rules/tauri-conventions.md` — this skill orchestrates, it does not restate either.

## When NOT to use

- The app is a web app, CLI, or server with no desktop-shell requirement → use the normal `/feature`/`/architect` language dispatch instead.
- A desktop app is wanted but the user has explicitly requested Electron or a native toolkit (e.g. Swift/WinForms) instead of Tauri → follow the explicit request; do not default to Tauri over an explicit choice.
- Reviewing plain Rust or plain frontend code with no Tauri surface (no `#[tauri::command]`, no `capabilities/*.json`, no `@tauri-apps/api` usage) → use the normal Rust/JS review path; `tauri-reviewer` will itself decline non-Tauri files.

## Usage

```
/tauri                          # show this help
/tauri new [name]                # scaffold a new Tauri v2 app (prereq check + create-tauri-app)
/tauri setup                     # check/install Tauri prerequisites only, no scaffold
/tauri design                    # invoke tauri-architect for a new feature or restructure
/tauri add-plugin <name>         # add an official Tauri plugin to the project
/tauri build                     # production build/bundle, with a pre-flight capability/CSP check
/tauri review [paths]            # invoke tauri-reviewer on the given files (defaults to git diff)
/tauri debug <description>       # invoke tauri-debugger on a build/runtime failure
```

## Workflow

### 1. Parse the subcommand

Split `$ARGUMENTS` on the first space. The first word is the subcommand.

- Empty or `help` → print **Usage** and stop.
- Not one of `new`, `setup`, `design`, `add-plugin`, `build`, `review`, `debug` → print **Usage** and stop.
- Dispatch to the matching step.

### 2. Dispatch — `new`

1. **Confirm the desktop-app request is a good fit for Tauri.** If the user's request already named a different framework, stop — do not override an explicit choice.

2. **Run the prerequisite check.**
   ```bash
   bash ~/.claude/skills/tauri/check_prereqs.sh
   ```
   If it exits `1`, present the gaps and their install commands from `rules/tauri-setup.md`. **If any gap requires `sudo`: stop and get explicit confirmation before running it.** Non-`sudo` gaps (`rustup`, user-scoped package manager installs) can proceed without an extra confirmation pass.

3. **Must determine the package manager and frontend framework.** Check for an existing lockfile (`pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`) to pick the package manager; if none exists, use `AskUserQuestion` to ask (options: npm, pnpm, yarn, cargo). Use `AskUserQuestion` to ask which frontend framework the user wants (options: React, Vue, Svelte, SolidJS, vanilla), unless they have already stated a preference — in that case apply `tauri-architect`'s selection table (team's existing skillset first) instead of asking.

4. **Scaffold using the pinned package-manager form from `rules/tauri-setup.md`'s Mandatory Behaviors** — never the raw installer script.

5. **Apply `rules/tauri-conventions.md`'s baseline conventions** to the freshly scaffolded project before the first commit.

6. **If the app has non-trivial structure beyond the template** (multiple command domains, persistent state, more than one window): invoke `tauri-architect` before writing feature code. For a simple template-as-is app, skip straight to implementation.

### 3. Dispatch — `setup`

Run the same prerequisite check as `new` step 2, without scaffolding anything. Use this when Tauri is being added to an existing frontend project (`tauri init` inside it) rather than started from scratch.

### 4. Dispatch — `design`

Invoke the `tauri-architect` agent. Must gather first: the app's purpose, target platforms (desktop OSes; mobile only if explicitly requested), any existing `src-tauri/` structure, and the specific feature or restructure being designed. Must present the agent's command surface, capability plan, state design, and plugin list to the user. **If the user has not explicitly approved the design: stop and do not proceed to implementation.**

### 5. Dispatch — `add-plugin`

**Precondition:** a plugin name was given after `add-plugin`. **If missing: stop and ask which plugin.**

1. Must verify the plugin maps to a concrete requirement — do not add speculatively (see `tauri-architect`'s plugin table for the common mappings).
2. Run the CLI command:
   ```bash
   npm run tauri add <plugin>   # or the project's package-manager equivalent
   ```
3. Must add the plugin's required capability entries to `capabilities/*.json` in the same change — an installed-but-ungranted plugin permission is a common source of confusing runtime "permission denied" errors.

### 6. Dispatch — `build`

**Pre-flight check before running a release build:**

1. Must verify `tauri.conf.json`'s `app.security.csp` is not `null`.
2. Must verify no `capabilities/*.json` grants a `*:default` wildcard.
3. Must verify the updater plugin (if configured) has signature verification enabled.

**If any check fails: stop and flag it** — these are exactly the `tauri-reviewer` Must Fix signals, and shipping a release bundle with them is materially worse than catching them in dev.

Then run:
```bash
npm run tauri build   # or the project's package-manager equivalent
```

If the build fails, dispatch to `debug` (step 8) rather than guessing at the fix.

### 7. Dispatch — `review`

**Identify scope.** If no path argument: `git diff --name-only HEAD`. Filter to files matching Tauri patterns (`#[tauri::command]`, `capabilities/*.json`, `tauri.conf.json`, `@tauri-apps/api` usage) — if none match, report that and stop (mirrors `tauri-reviewer`'s own precondition, checked here first to avoid an unnecessary agent call).

Invoke the `tauri-reviewer` agent on the matched files with `model: "haiku"` — reviewer output is structured findings against `rules/findings-format.md` (file:line, what, why, fix), well within Haiku's range. Report the findings.

### 8. Dispatch — `debug`

**Precondition:** a description of the failure was given. **If missing: stop and ask** for the error message, the command that was running (`tauri dev`/`tauri build`/a specific `invoke()` call), and the OS.

Invoke the `tauri-debugger` agent with the failure description and any available error output. Report root cause, evidence, fix, and regression risk per `rules/debug-process.md`.

### 9. Final verification step

- `new` → prerequisite check passed (or gaps were explicitly confirmed and installed), project scaffolded via a pinned command, CSP set, capability file reviewed
- `setup` → prerequisite check report delivered
- `design` → user has explicitly approved the proposal before any implementation starts
- `add-plugin` → plugin installed and its capability entries added in the same change
- `build` → pre-flight checks passed before the build ran, or the build was blocked with the specific failing check named
- `review` → findings reported per `rules/findings-format.md`, or the "no Tauri patterns" skip message if scope didn't match
- `debug` → report includes all four of root cause, evidence, fix, and regression risk

If any of the above is incomplete, do not report the subcommand as done.

## Rules (apply across all subcommands)

- `rules/tauri-setup.md` is authoritative for dependency detection and installation, including the scaffold-command and `sudo`-confirmation mandates — do not restate its content here.
- `rules/tauri-conventions.md` is authoritative for project structure, IPC, capabilities, and state management — do not restate its checklist here.
- `design` never proceeds to implementation before the user has explicitly approved the proposal.
- **`disable-model-invocation` is deliberately unset.** `new` and `build` have real side effects (scaffolding a directory; producing a release artifact), which would normally argue for it — but the whole point of this skill is that Claude auto-invokes it when a desktop app is requested; blocking model invocation would silently defeat that. The side effects are instead gated inline: explicit confirmation before any `sudo` install (step 2.2), explicit user approval before `design` proceeds to implementation, and hard-stop pre-flight checks before `build` runs. Do not add `disable-model-invocation: true` without re-confirming this trade-off with the user first.
