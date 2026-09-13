---
description: Electron IPC canonical patterns — `ipcRenderer.invoke`/`ipcMain.handle` for request/reply, `ipcRenderer.send`/`ipcMain.on` for one-way, `webContents.send` for main→renderer push, `MessagePort` for renderer↔renderer. Includes `contextBridge` wrapper shape, structured-clone constraints, and channel-naming conventions.
paths:
  - "**/electron.{js,ts,cjs,mjs}"
  - "**/main.{js,ts,cjs,mjs}"
  - "**/main/**/*.{js,ts,cjs,mjs}"
  - "**/preload.{js,ts,cjs,mjs}"
  - "**/preload/**/*.{js,ts,cjs,mjs}"
  - "**/renderer/**/*.{js,ts,jsx,tsx,cjs,mjs}"
---

# Electron IPC

Every renderer↔main interaction in a `contextIsolation: true` app goes through one of four IPC shapes. Picking the wrong shape produces the same class of bugs repeatedly: manually-correlated replies where `invoke` was the right tool, event-object leaks that undo isolation, and channel-name interpolation from the renderer. This rule is the taxonomy plus the wrapper shape.

**This is an intentional taxonomy — do not simplify it away.** "Just use `send`+`on` for everything" pushes request-reply correlation into userland, where it drifts and leaks. Use the pattern that matches the direction and cardinality.

## The four canonical patterns

### 1. Renderer → main, one-way (`send` / `on`)

Fire-and-forget from renderer. No return value expected. Use for menu clicks, telemetry, "open devtools", "quit app".

```ts
// preload
contextBridge.exposeInMainWorld('menu', {
  itemClicked: (id: string) => ipcRenderer.send('menu:item-clicked', id),
});

// main
ipcMain.on('menu:item-clicked', (event, id) => {
  if (!isTrustedFrame(event.senderFrame)) return;
  handleMenuItem(id);
});
```

### 2. Renderer → main, request/reply (`invoke` / `handle`) — preferred default

Promise-returning. Use for anything with a result: dialogs, DB reads, file operations, config lookups. This is the default — reach for `send`/`on` only when there is genuinely no reply.

```ts
// preload
contextBridge.exposeInMainWorld('config', {
  read: (): Promise<Config> => ipcRenderer.invoke('config:read'),
});

// main
ipcMain.handle('config:read', async (event) => {
  if (!isTrustedFrame(event.senderFrame)) throw new Error('untrusted');
  return await loadConfig();
});
```

Thrown errors cross the wire as a rejection but **only `message` survives** — types, `cause`, and stack are lost. Map to a stable error code inside the handler if the renderer needs to branch on it.

### 3. Main → renderer, push (`webContents.send` / `ipcRenderer.on`)

Server-push updates from main to a specific renderer. Use for progress bars, menu-driven state changes, filesystem-watch notifications.

```ts
// main
win.webContents.send('progress:update', { done: 42, total: 100 });

// preload — wrap the listener so `event.sender` never crosses the bridge
contextBridge.exposeInMainWorld('progress', {
  onUpdate: (cb: (p: Progress) => void) => {
    const listener = (_event: unknown, payload: Progress) => cb(payload);
    ipcRenderer.on('progress:update', listener);
    return () => ipcRenderer.removeListener('progress:update', listener);
  },
});
```

Always return an unsubscribe function. Without one the renderer accumulates listeners on every re-render.

### 4. Renderer ↔ renderer via `MessagePort`

There is no direct renderer-to-renderer channel. Two options:

- **Route through main** — simplest; renderer A calls `invoke('bus:emit', …)`, main fans out via `webContents.send` to renderer B. Fine for low-frequency events.
- **Transfer a `MessagePort`** — main creates a `MessageChannelMain`, `postMessage`s one port to each renderer, then the renderers talk peer-to-peer. Use when the message rate would swamp main.

## `contextBridge` wrapper shape (mandatory)

Every exposed API follows this shape:

1. **One wrapper function per operation.** No `send(channel, …)` / `invoke(channel, …)` exposed — the renderer must not choose the channel.
2. **Channel names are string literals inside preload/main only.** Never templated with renderer input.
3. **Listener callbacks are wrapped** before being registered with `ipcRenderer.on` so `event` and `event.sender` stay in the preload world.
4. **Every `on` returns an unsubscribe function.** The renderer is responsible for calling it on unmount / dispose.
5. **Payloads are Structured-Clone-safe.** No functions, DOM nodes, class instances with methods, `Map`/`Set` of non-cloneable values, or native handles. Plain JSON-shaped objects, `ArrayBuffer`, `Blob`, `Date` are OK.

## Channel naming

- `namespace:verb-object` — `config:read`, `window:minimize`, `updater:check`.
- Lowercase, colon-separated, no dots (dots collide with typical event naming conventions in some tools).
- One namespace per feature; a handler collision is a symptom that two features share too much.

## Recognition Signals

| Signal | Fix |
|---|---|
| `ipcRenderer.send('foo', …)` followed by `ipcRenderer.on('foo:reply', …)` with a correlation id | Use `invoke`/`handle` — the correlation is built in |
| `contextBridge.exposeInMainWorld('ipc', ipcRenderer)` or spread of `ipcRenderer` methods | Expose narrow wrappers only |
| Exposed function accepts `(channel: string, …args)` — renderer picks the channel | Split into one wrapper per channel; channel is a literal inside preload |
| Exposed `on` returns `void` (no unsubscribe) | Return the unregister function from the wrapper |
| Listener callback exposed directly, i.e. `on: (channel, cb) => ipcRenderer.on(channel, cb)` | Wrap `cb` so it receives only the payload; `event` never crosses the bridge |
| Handler in main assumes payload shape without validation | Validate type/shape before use (see `rules/electron-security.md`) |
| Handler in main returns raw `Error` objects with stack traces to renderer | Return a stable error code/message; log the detail server-side |
| Main→renderer notification requires knowing which window to target and code loops all `BrowserWindow`s | Track the specific `webContents` (per feature) or use a topic/pub-sub abstraction |
| `webContents.send` called from a `will-quit` / `before-quit` handler | The renderer may already be gone; guard with `!wc.isDestroyed()` |
| Payload includes a class instance with methods, a `Function`, or a native handle | Convert to a plain object before send; the receiver gets `{}` or a `DataCloneError` |
| Same channel name string appears in multiple files with no shared constant | Define channel constants in a shared, main+preload-only module |

## Mandatory Behaviors

**Default to `invoke`/`handle`.** Fall back to `send`/`on` only when there is no reply.

**Wrap every `on` and return an unsubscribe.** Callers rely on it for cleanup on component unmount.

**Validate every payload in the handler.** The `contextBridge` boundary does not validate — it only serializes. See `rules/electron-security.md` § IPC handler side.

**Never let the renderer choose the channel.** Channel string literals live in preload/main, not in the renderer.

**When reviewing code**, report per `rules/findings-format.md`:
- **Must Fix**: any handler that skips argument validation on a channel touching filesystem/shell/network; `contextBridge` exposing `ipcRenderer`; renderer-supplied channel names.
- **Should Fix**: `send`/`on` used for request/reply with hand-rolled correlation; missing unsubscribe from an exposed `on` wrapper; handler returning `Error` objects with stack traces.
- **Consider**: channel constants scattered across files; per-feature `webContents` tracking could replace an all-windows broadcast.

## Pragmatism Guard

- **Very-low-frequency events** may skip the `MessagePort` approach and route through main; the extra hop is negligible.
- **Type-only exports** (a shared `.d.ts` for payload types) between renderer and main are fine — do not confuse them with runtime imports.
- **A `send` call with no `on`** is legitimate for pure telemetry; do not mechanically upgrade to `invoke`.

## Anti-Patterns to Avoid

- **Handrolling request/reply with `send`+`on` and a correlation id.** That is what `invoke`/`handle` exists to remove.
- **Exposing `ipcRenderer.on` verbatim.** The callback signature includes `event`, which leaks the entire main-world API.
- **Broadcasting from main via a loop over `BrowserWindow.getAllWindows()`.** Every window receives the event, including ones that shouldn't. Keep a targeted `webContents` reference per feature.
- **Channel names computed from user input** — `` `chat:${roomId}` `` on the renderer side. Move the composition into main; renderer passes `roomId` as a payload argument on a single channel.

## Cross-references

- `rules/electron-security.md` — payload validation, sender-origin checks, contextBridge exposure rules. This rule owns the shape; that rule owns the security guarantees.
- `rules/electron-process-model.md` — which process runs each side of the boundary.
