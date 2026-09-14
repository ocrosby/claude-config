---
description: Electron process model — what runs in main, renderer, preload, and utility processes; which APIs are available in each; when to spawn a utility process; native-module ABI and `@electron/rebuild`; Electron support-window policy.
paths:
  - "**/electron.{js,ts,cjs,mjs}"
  - "**/main.{js,ts,cjs,mjs}"
  - "**/main/**/*.{js,ts,cjs,mjs}"
  - "**/preload.{js,ts,cjs,mjs}"
  - "**/preload/**/*.{js,ts,cjs,mjs}"
  - "**/renderer/**/*.{js,ts,jsx,tsx,cjs,mjs}"
---

# Electron Process Model

Electron runs at least two processes and often four. Code that mixes them silently — a renderer that requires a Node module, a main-process handler that blocks on CPU work, a preload that touches the DOM — produces the bugs that dominate Electron support channels. This rule names each process's job and constraints so the code that goes into each is decided deliberately, not by copy-paste.

## The four processes

| Process | Purpose | Has | Does NOT have (by default) |
|---|---|---|---|
| **Main** | App lifecycle, native OS APIs, window management, IPC orchestrator | Node.js APIs, Electron `app`/`BrowserWindow`/`Menu`/`Tray`/`dialog`/`shell`/`session`/`net`, single event loop | DOM, `window`, `document`, web APIs |
| **Renderer** | Chromium page — HTML/CSS/JS UI | DOM, all standard web APIs, `postMessage`, workers | `require`, Node APIs, Electron modules, `process` (except a stub) |
| **Preload** | Bridge between renderer's isolated world and main | DOM, `contextBridge`, `ipcRenderer`, limited Node in sandboxed mode (`events`, `timers`, `url`, polyfilled `Buffer`/`process`), full Node when unsandboxed | The renderer's `window` — a separate V8 context |
| **Utility** | CPU-bound, crash-prone, or untrusted Node work spawned from main | Full Node.js, own event loop, `MessagePort` to renderers | Electron modules (`app`, `BrowserWindow`, etc.) |

**Rule of placement**: OS + orchestration → main; CPU-heavy or crashy Node → utility; UI + web APIs → renderer; bridge → preload. Anything else is a code smell.

## Recognition Signals — code in the wrong process

| Signal | Belongs in |
|---|---|
| Renderer file `require`s `fs`, `path`, `child_process`, or any Electron module | Move to main; expose the needed operation via IPC through preload |
| Main file touches `document`, `window`, or `navigator` | Move to renderer; if the operation needs OS access too, split it across processes with IPC |
| Preload manipulates the page's DOM directly | Move DOM work to the renderer bundle; preload only bridges APIs |
| Main handler calls a CPU-heavy sync function (image resize, crypto hash of a large blob, ML inference) | Spawn a utility process via `utilityProcess.fork`; block main only for orchestration, not compute |
| Native module `require`d in main hangs the event loop on I/O | Move to a utility process; native modules that don't release the loop block every window |
| Long-running Node work sits inside a `Promise` and races the UI | Utility process — Promises share the main event loop with window/menu handling |
| Preload attaches a property directly to `window` (`window.api = …`) with `contextIsolation: true` | Use `contextBridge.exposeInMainWorld` — direct assignment silently fails across the isolated world |
| Renderer imports a shared library that transitively requires Node | Split the library — put Node-only code behind an IPC boundary |
| Preload bundle imports the same `.d.ts` as renderer but the runtime code differs | Fine as a type-only import; guard with build-tool `type: 'module'` / `import type` |

## Native modules and `@electron/rebuild`

Native (`.node`) modules built against stock Node.js will crash on `require` inside Electron because Electron's `NODE_MODULE_VERSION` differs. Rules:

- **Rebuild native modules against Electron's headers** using `@electron/rebuild` (formerly `electron-rebuild`).
- **Electron Forge auto-runs `@electron/rebuild`** on install and package. Hand-rolled setups need to add it as a `postinstall` script or invoke it in packaging.
- **Prefer N-API (`node-api`) modules** — ABI-stable, no rebuild needed. Check `package.json` for `"engines": { "node": ">=X" }` and `binary` fields; the tag `node-api` in the module's README signals stability.
- **The tell-tale error** is `Error: The module '/…/foo.node' was compiled against a different Node.js version using NODE_MODULE_VERSION $XYZ. This version of Node.js requires NODE_MODULE_VERSION $ABC.`

## Utility processes — when to spawn

Signals that main is doing the wrong work:

| Signal | Fix |
|---|---|
| CPU profile shows main event loop blocked > 50 ms | Move the blocking work to a utility process |
| Crashy native code (image codec, PDF, ML) linked into main | Utility process — a crash there does not take down the app |
| Untrusted script execution requested (user plugins, macro DSL) | Utility process with a `sandbox: true` renderer-style boundary |
| High-frequency IPC between two renderers routed through main | Skip main entirely — main creates a `MessageChannelMain`, transfers one port to each renderer |

Spawn with `utilityProcess.fork(modulePath, args, { serviceName: '…' })`. Communicate via `postMessage`/`MessagePort`. Do not `require('electron')` inside a utility process — those modules are not available.

## Support window and versioning

- **Release cadence:** new major every 8 weeks, tracking Chromium.
- **Supported majors:** the newest three concurrently receive patches; older majors receive nothing.
- **Pin the series, not a frozen minor** — patches ship on the newest minor of each supported series only.
- **Upgrade tempo:** budget a major bump every ~6 months to stay inside the support window. Falling out means shipping unpatched Chromium.

## Mandatory Behaviors

**When placing new code**: name the process it will run in before you write the first line. If two placements are plausible, split the code — one file per process. Do not write "runs in both" modules.

**When adding a native module**: verify it is N-API or ensure `@electron/rebuild` runs on install/package. State which in the PR.

**When main's event loop blocks**: move the blocking work to a utility process. Async does not un-block CPU work — it only defers it within the same loop.

**When editing existing code**: if you touch a file that has a recognition signal above, fix it in the same change or file a follow-up. Do not paper over with `nodeIntegration: true` — see `rules/electron-security.md`.

**When reviewing code**, report per `rules/findings-format.md`:
- **Must Fix**: Node/Electron modules `require`d in renderer code (usually paired with `nodeIntegration: true`, both flagged); native module without rebuild strategy; CPU work synchronous in main.
- **Should Fix**: preload doing DOM work; long-running Promise chain in main that should be a utility process; Electron major older than the newest supported.
- **Consider**: renderer↔renderer routed through main at high frequency where `MessagePort` would remove the hop.

## Pragmatism Guard

- **Small apps** (single window, no native modules, no CPU work) can live with main + renderer + preload; no utility process needed.
- **Renderers that never load untrusted content** may skip `sandbox: true` — but every other security default still applies (see `rules/electron-security.md`).
- **Type-only imports across processes** (`import type { Foo } from '../shared/types'`) are fine; the compiler erases them.

## Anti-Patterns to Avoid

- **"Just enable `nodeIntegration`"** to run Node code in the renderer. That is the shortcut that this rule and `rules/electron-security.md` both exist to prevent.
- **`electron-remote` / `@electron/remote`** to reach main APIs from the renderer synchronously. The `remote` module was removed for security reasons; `@electron/remote` is a community continuation and is not recommended for new code. Use IPC.
- **Spawning `child_process.fork` from main** for Electron-style work. Use `utilityProcess.fork` — it hooks into Electron's lifecycle, integrates with IPC, and can hold `MessagePort`s to renderers.
- **Blocking main "briefly" for a hash or a resize.** Every window in the app is frozen for the duration. Move it out.

## Cross-references

- `rules/electron-security.md` — what to disable in each process; this rule owns what remains.
- `rules/electron-ipc.md` — the shapes of the boundaries between processes.
