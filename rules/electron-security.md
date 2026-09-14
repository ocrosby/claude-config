---
description: Electron security defaults — sandbox on, nodeIntegration off, contextIsolation on, strict CSP, permission/nav/window-open handlers, `contextBridge` discipline, `shell.openExternal` and IPC-origin validation. Fires on Electron main-process, preload, and `BrowserWindow`-configuring files.
paths:
  - "**/electron.{js,ts,cjs,mjs}"
  - "**/main.{js,ts,cjs,mjs}"
  - "**/main/**/*.{js,ts,cjs,mjs}"
  - "**/preload.{js,ts,cjs,mjs}"
  - "**/preload/**/*.{js,ts,cjs,mjs}"
  - "**/forge.config.{js,ts,cjs,mjs}"
  - "**/electron-builder.{yml,yaml,json,js,ts}"
---

# Electron Security

Electron gives web content direct access to Node.js and the OS unless every switch is set correctly. A single XSS in a page that runs with the wrong `webPreferences` becomes remote code execution. This rule enumerates the non-negotiable defaults from the Electron security page (https://www.electronjs.org/docs/latest/tutorial/security) and the recognition signals for how they fail.

**This is an intentional set of design decisions — do not simplify it away.** Every insecure default has a "just for now" argument that ships. Turning `nodeIntegration` back on to unblock a demo is exactly how the class of bugs this rule prevents reaches production. If a workaround is genuinely required, name the specific threat model and add a comment on the line naming the deviation.

## Recognition Signals

### `BrowserWindow` / `webPreferences` misconfiguration

| Signal | Mitigation |
|---|---|
| `nodeIntegration: true` in any `webPreferences` | Set `nodeIntegration: false` (default since v5); use a preload + `contextBridge` for the specific APIs the page needs |
| `contextIsolation: false` | Set `contextIsolation: true` (default since v12); expose APIs via `contextBridge.exposeInMainWorld` |
| `sandbox: false` on windows that load remote or third-party content | Set `sandbox: true`; preload gets limited Node access (only `events`, `timers`, `url`, polyfilled `Buffer`/`process`) |
| `webSecurity: false` | Remove the flag; fix the cross-origin need with a proper protocol or CORS |
| `allowRunningInsecureContent: true` | Remove; load everything over HTTPS/WSS |
| `experimentalFeatures: true` or `enableBlinkFeatures` set | Remove; these ship pre-release Chromium code with no security review |
| `<webview>` used with `allowpopups`, or `will-attach-webview` handler absent | Attach a `will-attach-webview` handler that whitelists `src` and strips dangerous options |
| No `Content-Security-Policy` header/meta tag on loaded pages | Set a strict CSP (at minimum `default-src 'self'`); do not include `'unsafe-eval'` |
| Loading `http://…` in `loadURL` / `loadFile` chain | Use HTTPS or an in-app custom protocol registered via `protocol.handle` |

### Preload / `contextBridge` leaks

| Signal | Mitigation |
|---|---|
| `contextBridge.exposeInMainWorld('…', ipcRenderer)` or `{ ipcRenderer }` | Expose narrow wrapper functions only — never the module itself |
| Exposed function returns `event` or `event.sender` from an `ipcRenderer.on` callback | Wrap the callback so only the payload arguments cross the bridge |
| Preload attaches to `window` directly (`window.api = …`) with `contextIsolation: true` | Use `contextBridge.exposeInMainWorld`; direct assignment silently fails across the isolated context |
| `require('electron')` returned to the renderer via any exposed value | Never — even a transitive reference collapses isolation |
| Renderer can invoke any channel because preload exposes `send`/`invoke` with the channel as a parameter | Expose one wrapper per operation (`{ readConfig: () => ipcRenderer.invoke('config:read') }`) — no dynamic channel names |

### IPC handler side (main process)

| Signal | Mitigation |
|---|---|
| `ipcMain.handle` / `ipcMain.on` handler that trusts arguments without validation | Validate every argument (type, shape, length, allowed values) before use |
| Handler that does not check `event.senderFrame.origin` (or `event.senderFrame.url`) | Reject frames that aren't the app's own origin — a compromised iframe otherwise reaches every handler |
| Handler that opens a file/URL based on a renderer-supplied path | Resolve to absolute, verify it lives under an allowed base directory (path-confinement — see OWASP A01) |
| `shell.openExternal(userSuppliedUrl)` without allowlist check | Validate scheme (`https:` only) and host against an allowlist; block `file://`, `javascript:`, `data:` |
| Errors thrown from `handle` handlers propagated to renderer with stack traces | Map to a stable error code/message; keep the stack server-side |

### Navigation, window creation, permissions

| Signal | Mitigation |
|---|---|
| No `webContents.setWindowOpenHandler` — `window.open` and `target="_blank"` open arbitrary URLs | Set a handler that returns `{ action: 'deny' }` by default and allowlists known destinations |
| No `will-navigate` listener — a malicious link can navigate the main frame to an attacker page | Attach `will-navigate`; call `event.preventDefault()` for anything outside the app's origin allowlist |
| No `session.setPermissionRequestHandler` — camera/mic/geolocation prompts approve silently or by default | Attach a handler that denies by default and allowlists only the origins that need the permission |
| `webContents.on('will-attach-webview', …)` missing on any window that could host `<webview>` | Attach; strip `nodeintegration`, validate `src`, force `contextIsolation: true` |

### Packaging, fuses, and distribution

| Signal | Mitigation |
|---|---|
| macOS build shipped unsigned or unnotarized | Sign with `@electron/osx-sign` and notarize via `@electron/notarize` (or Forge/Builder wrappers) — required for auto-update on macOS |
| Windows build shipped without Authenticode signature | Sign the installer with a valid code-signing cert (Squirrel maker or Builder `certificateFile`) |
| Electron major older than the newest three (support window) | Upgrade to a supported major; older majors receive no Chromium security patches |
| `runAsNode` / `enableNodeCliInspectArguments` fuses left enabled in production | Disable via `@electron/fuses` unless the app genuinely needs them |
| `asar` integrity fuse disabled | Enable `EnableEmbeddedAsarIntegrityValidation` and `OnlyLoadAppFromAsar` for tamper resistance |
| Autoupdater configured against HTTP or a non-signed feed | Use HTTPS + code-signed updates only |

## Mandatory Behaviors

**When writing Electron code**: default to the secure form. Every `BrowserWindow` constructor must include `webPreferences` with `sandbox: true, contextIsolation: true, nodeIntegration: false`. Every preload must use `contextBridge`. Every `ipcMain.handle`/`.on` must validate arguments and the sender frame's origin. Every `webContents` must have `setWindowOpenHandler` and a `will-navigate` listener.

**When exposing an API through `contextBridge`**: expose narrow, purpose-named wrapper functions. Never `ipcRenderer`, never `require`, never Electron modules, never event objects, never a function that takes a channel name as a parameter.

**When editing existing code**: if you touch a `BrowserWindow` or preload and any signal above fires, fix it in the same change. Do not walk past.

**When reviewing code**, report findings per `rules/findings-format.md`:
- **Must Fix**: `nodeIntegration: true`, `contextIsolation: false`, `webSecurity: false`, `allowRunningInsecureContent: true`, `contextBridge` exposing `ipcRenderer`/`require`/Electron modules, `ipcMain.handle` with no argument validation on a channel that touches the filesystem/shell/network, `shell.openExternal` with unvalidated input, HTTP feed used for auto-update, unsigned macOS build with `autoUpdater` wired up.
- **Should Fix**: `sandbox: false` on a window loading local content only, missing `setWindowOpenHandler`, missing `will-navigate`, missing CSP, missing `setPermissionRequestHandler`, missing sender-origin check on an IPC handler, Electron major within the support window but not on the newest.
- **Consider**: additional defense-in-depth (fuses tightened, CSP tightened beyond `default-src 'self'`, `asar` integrity fuse enabled).

## Pragmatism Guard

Do not apply this rule when:

- **The window loads only bundled local assets** and the app has no `<webview>`, no third-party iframes, and no dynamic navigation. `sandbox: false` may be a considered choice; state it in a comment and keep every other flag secure.
- **The renderer is a devtools panel or a test fixture** with no user-supplied content. Note the scope in a comment.
- **A workaround is temporary** and gated behind an explicit build flag (`ELECTRON_INSECURE_DEV=1`). The flag must not default on and must be filtered out at package time.

Exceptions must be inline-commented with the specific threat model that permits the deviation. "It didn't work otherwise" is not an exception.

## Anti-Patterns to Avoid

- **Turning off `contextIsolation` because "preload can't see `window`".** That is the isolation working — use `contextBridge` instead.
- **Wrapping `ipcRenderer` in an object and calling it "safe".** Any object holding a live reference to `ipcRenderer` is `ipcRenderer` — the renderer can call every channel.
- **Passing raw callbacks to `ipcRenderer.on` through `contextBridge`.** The callback receives `event` whose `.sender` is a full `webContents` — a leak of the main-world API.
- **Using `shell.openExternal` on any URL the renderer supplied without allowlist validation.** `javascript:` and `file:` URLs are shell-openable and route through the OS.
- **Assuming a same-team origin is trustworthy.** Every `ipcMain` handler validates its inputs regardless of who wrote the caller.

## Cross-references

- `rules/owasp-top-10.md` — A01 (access control / SSRF / path traversal), A03 (supply chain / signing), A04 (crypto — TLS-only for update feeds), A05 (injection — CSP, `will-navigate`), A07 (auth in Electron apps), A08 (integrity — code signing, asar), A10 (fail-closed on IPC errors).
- `rules/electron-ipc.md` — canonical IPC patterns; this rule owns the security guarantees, that rule owns the shape.
- `rules/electron-process-model.md` — which APIs are available where; this rule owns what to disable, that rule owns what remains.
