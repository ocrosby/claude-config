# Tauri Application Conventions

Tauri apps have two runtimes talking to each other across a trust boundary: a Rust backend with OS-level privileges and a webview frontend rendering arbitrary HTML/JS. Every convention below exists because that boundary is where Tauri apps actually break — either a capability grants more than the frontend needs (security), or a command panics and takes the whole IPC round-trip down with it (correctness), or the two sides drift out of sync on what a message means (integration bugs unique to this framework, not to Rust or to JS alone).

For installing the toolchain, see `rules/tauri-setup.md` — this rule does not repeat it. For general Rust and general JS/TS conventions, defer to whatever language-level rules the project already uses; this rule covers only what is specific to Tauri.

## Project structure

```
src-tauri/
├── Cargo.toml
├── tauri.conf.json          -- app config: identifier, bundle, security.csp, windows
├── capabilities/
│   └── default.json         -- per-window permission grants (default-deny)
└── src/
    ├── main.rs               -- entry point, calls lib.rs's run()
    ├── lib.rs                 -- Builder setup, .manage(), .invoke_handler()
    └── commands/              -- #[tauri::command] functions, one module per domain area
<frontend framework's own layout>  -- React/Vue/Svelte/SolidJS/vanilla, at repo root or src/
```

Frontend and backend are two separate build systems (Vite/webpack/etc. for the frontend, Cargo for the backend) wired together only by `tauri.conf.json`'s `build.devUrl` / `build.frontendDist` and the `@tauri-apps/api` package. Do not blur this boundary by importing Rust code paths from the frontend build config or vice versa.

## Recognition Signals

### IPC commands — when the backend/frontend boundary is the problem

| Signal | Convention |
|---|---|
| `#[tauri::command]` function contains `.unwrap()` or `.expect()` | A panic inside a command crashes the async runtime task handling that call and returns an opaque error to the frontend. Return `Result<T, E>` with a serializable `E` instead |
| Command parameter is a raw `String` used to build a file path or shell invocation | Validate/sanitize before use — this is the same injection surface as an HTTP handler (`rules/owasp-top-10.md` A05) |
| Command performs blocking I/O (file read, DB query, HTTP call) and is not `async fn` | Blocking the async executor stalls every other command on that thread pool — mark it `async fn` and await |
| Frontend calls `invoke()` without a `.catch()` or `try/catch` | Unhandled command errors vanish silently in the webview console — every `invoke()` needs error handling (`rules/owasp-top-10.md` A10) |
| Backend needs to push data to the frontend without being asked | Use `app.emit()` / `window.emit()` + frontend `listen()`, not a poll loop calling a command on an interval |
| Same shape of request/response duplicated across multiple commands | Define a shared serializable struct once in `commands/types.rs`, reuse across commands — mirrors `rules/docs-principles.md`'s Reusable structures principle for APIs |

### Capabilities and permissions — when the security boundary is the problem

| Signal | Convention |
|---|---|
| `capabilities/default.json` grants `"core:default"` or a plugin's `*:default` to every window | Scope grants to the specific window that needs them and the specific permission, not the bundle default |
| `fs` plugin permission has no `scope` (allows any path) | Add an explicit `scope` restricting to the app's data directory or a user-chosen path, never the whole filesystem |
| `shell` plugin's `execute` permission is granted without an `sidecar`/allowlist of binaries | Restrict to named, bundled sidecar binaries — an unscoped `shell:allow-execute` lets any JS in the webview run arbitrary system commands |
| `http` plugin permission has no `scope` restricting origins | Add an explicit allowlist of origins — an unscoped grant turns any XSS in the frontend into full outbound network access |
| A new command is added but never appears in any `capabilities/*.json` | The command is unreachable from the frontend by design in Tauri v2 — if the frontend needs it, add the specific permission; if it's Rust-internal, it may not need `#[tauri::command]` at all |
| `tauri.conf.json`'s `app.security.csp` is `null` or missing in a production build | An absent CSP allows any injected script to execute with full webview privileges — set an explicit CSP (`rules/owasp-top-10.md` A02) |

### State management

| Signal | Convention |
|---|---|
| Shared mutable state accessed from multiple commands without synchronization | Wrap in `Mutex<T>` or `RwLock<T>`, register via `.manage(AppState::new(...))`, access via `tauri::State<'_, AppState>` |
| A command holds a lock across an `.await` point | Drop the lock (or use an async-aware `tokio::sync::Mutex`) before awaiting — holding a sync `Mutex` across `.await` can deadlock the async runtime |
| Global `static` mutable state (`lazy_static`, raw `static mut`) used instead of managed state | Use `.manage()` — it is Tauri's dependency-injection point and is what `tauri::State` extraction relies on |

### Frontend/backend framework fit

| Signal | Convention |
|---|---|
| Frontend framework choice not yet decided for a new project | Match to the team's existing JS/TS skillset first; Tauri has no framework preference — React, Vue, Svelte, SolidJS, and vanilla are all first-class via `create-tauri-app` templates |
| Frontend needs server-side rendering | Tauri serves a static bundle — SSR frameworks must be configured for static export (e.g. Next.js `output: 'export'`), not left in SSR mode |
| App needs to run fully offline | Verify no frontend code path assumes a network-reachable dev server URL once bundled — `devUrl` is dev-only; the production bundle serves from `frontendDist` |

## Mandatory Behaviors

**Design the capability grant alongside the command, never after.** When adding a new `#[tauri::command]`, add its permission to the relevant `capabilities/*.json` in the same change — an ungranted command is a bug (unreachable feature); an over-scoped grant is a security hole. Neither should be deferred to "wire up permissions later."

**Every command returns a `Result`.** No exceptions for "this can't fail" — cross-IPC panics are worse than an error message, because the frontend sees an opaque rejection with no domain context. Define a project-wide command error type once (e.g. `#[derive(Serialize)] enum CommandError`) and reuse it.

**State that must survive app restarts goes through a plugin (`tauri-plugin-store`, `tauri-plugin-sql`), not hand-rolled file I/O in a command.** The store plugins already handle serialization, path resolution per-OS, and capability scoping correctly.

**Set an explicit CSP before any release build.** `null` is acceptable only for early local prototyping — flag it before a `tauri build` intended for distribution.

**When reviewing code**, apply `rules/findings-format.md`'s three buckets:
- **Must Fix**: `.unwrap()`/`.expect()` inside a `#[tauri::command]`; a capability grant scoped to `*:default` or an unscoped `fs`/`shell`/`http` permission; a command reachable from the frontend with no input validation; `security.csp: null` in a build intended for release
- **Should Fix**: a command doing blocking I/O without `async fn`; a lock held across an `.await`; a new command with no corresponding capability entry (even if currently unused by the frontend); duplicated request/response shapes across commands
- **Consider**: a poll loop that could be an `emit`/`listen` pair; a state struct that could move to a store plugin for persistence

## Pragmatism Guard

Do not apply this rule when:

- **The command is genuinely infallible** — e.g., returning a static build-time constant. `Result<T, Infallible>` ceremony for a value that cannot fail is noise; a plain return is fine.
- **A prototype explicitly marked as throwaway** (a spike branch, a demo that will never ship). Full capability scoping on a two-day proof-of-concept is disproportionate — but say so explicitly rather than silently skipping it, and re-apply this rule before the prototype becomes the real app.
- **The plugin being used already enforces its own scoping model** that supersedes the generic advice here (check the plugin's own docs) — follow the plugin's documented pattern instead of a generic capability shape.

## Anti-Patterns to Avoid

- **Granting `"core:default"` to make an error go away.** The error is almost always "this specific command/permission isn't granted" — grant that one thing, not the whole default set.
- **Treating the webview as a trusted client.** Any XSS, malicious dependency, or supply-chain-compromised frontend package runs with whatever the capability file grants — scope as if the frontend is hostile, because from a security-boundary perspective it effectively is.
- **Reimplementing file/HTTP/shell access by hand in a command instead of using the corresponding official plugin.** The plugins already handle per-OS path differences and capability-scoped permission checks; hand-rolled access bypasses that model entirely.
- **Leaving `devUrl` assumptions in code that also has to run from the bundled `frontendDist`.** Test the production build (`tauri build` or at minimum `tauri dev --release`), not just the dev-server-backed `tauri dev`.
