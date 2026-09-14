---
description: Use when working with Electron — scaffold a secure `BrowserWindow` + preload + IPC surface (scaffold), audit a repo against the Electron security checklist (audit), or plan packaging with signing/notarization/auto-update (package). Invoke as /electron <scaffold|audit|package>.
argument-hint: "<subcommand>"
aliases: electronjs
---

# Electron: Multi-Process Desktop Dispatcher

Use this skill for any Electron work. The dispatcher routes between three disjoint sub-cases: scaffolding a new window + IPC surface (`scaffold`), auditing an existing repo against the security checklist (`audit`), or planning packaging + auto-update (`package`).

**Rules the whole workflow leans on** (do not restate — read only when the workflow step below tells you to):

- `rules/electron-security.md` — `webPreferences` defaults, `contextBridge` discipline, IPC handler validation, packaging security.
- `rules/electron-ipc.md` — the four canonical IPC patterns and the wrapper shape.
- `rules/electron-process-model.md` — what runs where, when to spawn a utility process, native modules and `@electron/rebuild`.

**Agents this skill delegates to:**

- `electron-reviewer` — for the `audit` subcommand.
- `electron-architect` — for the `scaffold` and `package` subcommands when the design is non-trivial.
- `electron-debugger` — not invoked from this skill; invoke directly on a specific failure.

## Usage

```
/electron                  # show this help
/electron scaffold         # scaffold a secure BrowserWindow + preload + IPC surface
/electron audit            # audit the current repo against the security checklist
/electron package          # plan packaging: signing, notarization, updater, fuses
```

## Workflow

### 1. Parse the subcommand

Split `$ARGUMENTS` on the first space. First word is the subcommand.

- Empty or `help` → print **Usage** and stop.
- Not one of `scaffold`, `audit`, `package` → print **Usage** and stop.
- Dispatch to the matching step.

### 2. Dispatch — `scaffold`

Use this when creating a new Electron window, adding a preload, or adding a new IPC channel/feature namespace to an existing app.

**Do not run for major architectural decisions** (multi-window apps, utility processes, `<webview>` embedding, multi-renderer message channels). For those, delegate to the `electron-architect` agent first, then return here to lay down the files.

Read `~/.claude/skills/electron/scaffold.md` and apply its workflow:

- Secure `BrowserWindow` template with mandatory `webPreferences`
- Preload template using `contextBridge` with a one-wrapper-per-operation shape
- IPC feature namespace layout (`main/ipc/<feature>.ts` + `preload/wrappers/<feature>.ts` + `shared/ipc-schema.ts`)
- Strict CSP meta tag template
- `setWindowOpenHandler`, `will-navigate`, `setPermissionRequestHandler` wiring

### 3. Dispatch — `audit`

Use this when reviewing an existing Electron repo for security defects, IPC hygiene issues, and process-placement problems.

Delegate to the `electron-reviewer` agent. Provide it:

- The paths of every main-process file, preload file, and forge/builder config (glob: `**/electron.{js,ts}`, `**/main*.{js,ts}`, `**/preload*.{js,ts}`, `**/forge.config.*`, `**/electron-builder.*`).
- Any BrowserWindow / webPreferences occurrences (grep first, hand off the file list).

The agent applies its checklist and returns findings per `rules/findings-format.md`. Relay the report to the user.

**Fast-path scan (before delegating):** run `~/.claude/skills/electron/scan_insecure.sh <repo-root>` first — it emits a Markdown report of the most severe recognition signals (`nodeIntegration: true`, `contextIsolation: false`, `webSecurity: false`, `contextBridge` exposing `ipcRenderer`). If it finds nothing, the audit is unlikely to surface Must Fix items; still delegate for the full checklist.

### 4. Dispatch — `package`

Use this when planning distribution: picking Electron Forge vs electron-builder, wiring code signing, macOS notarization, Windows Authenticode, auto-updater backend, and Electron fuses.

Read `~/.claude/skills/electron/package.md` and apply its workflow:

- Forge vs Builder decision table
- macOS signing + notarization checklist (`@electron/osx-sign` + `@electron/notarize`, `APPLE_ID` / `APPLE_PASSWORD` / `APPLE_TEAM_ID` env vars)
- Windows Authenticode certificate wiring
- Auto-updater backend choice (Squirrel via `autoUpdater`, `update.electronjs.org` free service, `electron-updater`, self-hosted Hazel/Nuts)
- Recommended `@electron/fuses` configuration
- CI pipeline shape (matrix build on macOS/Windows/Linux, sign in CI or after-download)

For a first-time distribution plan, delegate design to `electron-architect` and use this file as the concrete checklist.

## Exceptions and hard stops

- **Do not add or restore `nodeIntegration: true`** for any reason not accompanied by an inline comment naming the specific threat model and a filed follow-up to remove it. See `rules/electron-security.md` § Anti-patterns.
- **Do not expose `ipcRenderer` through `contextBridge`.** No exceptions.
- **Do not use `@electron/remote`.** It re-introduces the security failures the `remote` module was removed for. Use IPC.
- **Do not use Spectron for tests.** Archived in 2022. Use Playwright's `_electron` API.
