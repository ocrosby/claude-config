# Electron: Scaffold Reference

Templates and layout for a new secure Electron window, preload, and IPC namespace. Loaded on demand by `/electron scaffold`.

## File layout target

```
src/
├── main/
│   ├── index.ts                     -- app.whenReady + createMainWindow
│   ├── security.ts                  -- setWindowOpenHandler, will-navigate, permission handler
│   ├── ipc/
│   │   └── <feature>.ts             -- one file per feature namespace
│   └── utility/                     -- utilityProcess.fork targets (optional)
├── preload/
│   ├── index.ts                     -- imports + contextBridge exposeInMainWorld calls
│   └── wrappers/
│       └── <feature>.ts             -- one file per feature, mirrors main/ipc/
├── renderer/
│   ├── index.html                   -- strict CSP meta
│   └── app.tsx
└── shared/
    └── ipc-schema.ts                -- type-only channel + payload types
```

Rules:

- `src/main` and `src/renderer` never import each other. Shared types live in `src/shared`, `import type` only.
- Channel constants live in `src/shared/ipc-schema.ts` and are imported from both main and preload — never from renderer.

## Templates

### `src/main/index.ts` — main window creation

```ts
import { app, BrowserWindow } from 'electron';
import path from 'node:path';
import { installSecurityHandlers } from './security';
import { registerConfigIpc } from './ipc/config';

const isDev = !app.isPackaged;

async function createMainWindow(): Promise<BrowserWindow> {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      // Mandatory security defaults — see rules/electron-security.md
      sandbox: true,
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: true,
      // Preload is loaded from the *packaged* location; do not use __dirname math that breaks under asar
      preload: path.join(__dirname, '../preload/index.js'),
    },
  });

  installSecurityHandlers(win);

  if (isDev) {
    await win.loadURL('http://localhost:5173');
  } else {
    await win.loadFile(path.join(__dirname, '../renderer/index.html'));
  }
  return win;
}

app.whenReady().then(async () => {
  registerConfigIpc();
  await createMainWindow();

  app.on('activate', async () => {
    if (BrowserWindow.getAllWindows().length === 0) await createMainWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
```

### `src/main/security.ts` — mandatory security handlers

```ts
import { BrowserWindow, shell, session } from 'electron';

const ALLOWED_EXTERNAL_HOSTS = new Set(['github.com', 'electronjs.org']);

export function installSecurityHandlers(win: BrowserWindow): void {
  // Deny all window.open unless allowlisted; open in system browser instead
  win.webContents.setWindowOpenHandler(({ url }) => {
    try {
      const parsed = new URL(url);
      if (parsed.protocol === 'https:' && ALLOWED_EXTERNAL_HOSTS.has(parsed.host)) {
        void shell.openExternal(url);
      }
    } catch {
      // malformed URL — deny silently
    }
    return { action: 'deny' };
  });

  // Prevent in-app navigation off the app's origin
  win.webContents.on('will-navigate', (event, url) => {
    const current = new URL(win.webContents.getURL());
    const target = new URL(url);
    if (target.origin !== current.origin) event.preventDefault();
  });

  // Deny all permission prompts by default; allowlist per-origin if needed
  session.defaultSession.setPermissionRequestHandler((_wc, _permission, callback) => {
    callback(false);
  });
}
```

### `src/shared/ipc-schema.ts` — channel constants + types

```ts
export const IPC = {
  configRead: 'config:read',
  configWrite: 'config:write',
} as const;

export interface Config {
  theme: 'light' | 'dark';
  fontSize: number;
}
```

### `src/main/ipc/config.ts` — one file per feature namespace

```ts
import { ipcMain } from 'electron';
import { IPC, type Config } from '../../shared/ipc-schema';
import { loadConfig, saveConfig } from '../config-store';

function isTrustedFrame(frame: Electron.WebFrameMain | null): boolean {
  if (!frame) return false;
  const origin = new URL(frame.url).origin;
  return origin === 'file://' || origin === 'http://localhost:5173';
}

function assertConfigShape(v: unknown): asserts v is Config {
  if (
    typeof v !== 'object' || v === null ||
    !('theme' in v) || !('fontSize' in v) ||
    (v as Config).theme !== 'light' && (v as Config).theme !== 'dark' ||
    typeof (v as Config).fontSize !== 'number' ||
    (v as Config).fontSize < 8 || (v as Config).fontSize > 72
  ) {
    throw new Error('invalid config payload');
  }
}

export function registerConfigIpc(): void {
  ipcMain.handle(IPC.configRead, async (event): Promise<Config> => {
    if (!isTrustedFrame(event.senderFrame)) throw new Error('untrusted frame');
    return await loadConfig();
  });

  ipcMain.handle(IPC.configWrite, async (event, next: unknown): Promise<void> => {
    if (!isTrustedFrame(event.senderFrame)) throw new Error('untrusted frame');
    assertConfigShape(next);
    await saveConfig(next);
  });
}
```

### `src/preload/index.ts` — contextBridge only

```ts
import { contextBridge } from 'electron';
import { config } from './wrappers/config';

contextBridge.exposeInMainWorld('api', {
  config,
});
```

### `src/preload/wrappers/config.ts` — narrow wrappers, no ipcRenderer exposed

```ts
import { ipcRenderer } from 'electron';
import { IPC, type Config } from '../../shared/ipc-schema';

export const config = {
  read: (): Promise<Config> => ipcRenderer.invoke(IPC.configRead),
  write: (next: Config): Promise<void> => ipcRenderer.invoke(IPC.configWrite, next),
};
```

For push notifications from main, wrap `ipcRenderer.on` and return an unsubscribe function:

```ts
// src/preload/wrappers/progress.ts
import { ipcRenderer, type IpcRendererEvent } from 'electron';

interface Progress { done: number; total: number; }

export const progress = {
  onUpdate: (cb: (p: Progress) => void): (() => void) => {
    const listener = (_event: IpcRendererEvent, payload: Progress) => cb(payload);
    ipcRenderer.on('progress:update', listener);
    return () => ipcRenderer.removeListener('progress:update', listener);
  },
};
```

### `src/renderer/index.html` — strict CSP

```html
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta
      http-equiv="Content-Security-Policy"
      content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https:"
    />
    <title>App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="./app.js"></script>
  </body>
</html>
```

CSP notes:

- `'unsafe-inline'` in `style-src` is common with CSS-in-JS libraries; move to hashes/nonces where possible.
- Never include `'unsafe-eval'` — it defeats the point.
- `connect-src` may need specific hosts if the app talks to APIs.

### Renderer type declaration

```ts
// src/renderer/global.d.ts
import type { config } from '../preload/wrappers/config';
import type { progress } from '../preload/wrappers/progress';

declare global {
  interface Window {
    api: {
      config: typeof config;
      progress: typeof progress;
    };
  }
}
```

## Adding a new IPC feature

1. Add channel constants to `src/shared/ipc-schema.ts`.
2. Add `src/main/ipc/<feature>.ts` with `ipcMain.handle` registrations, sender-frame validation, payload validation.
3. Add `src/preload/wrappers/<feature>.ts` with narrow wrapper functions.
4. Register the wrapper object in `src/preload/index.ts`.
5. Extend `Window` in `src/renderer/global.d.ts`.
6. Call `register<Feature>Ipc()` from `main/index.ts` inside `app.whenReady`.

## Anti-patterns to reject at scaffold time

- `nodeIntegration: true` — do not scaffold.
- `contextIsolation: false` — do not scaffold.
- `sandbox: false` on a window loading remote or third-party content — do not scaffold.
- `contextBridge.exposeInMainWorld('ipc', ipcRenderer)` — do not scaffold.
- Direct `window.api = …` assignment in preload — do not scaffold.
- Channel names built by templating on renderer-supplied strings — do not scaffold.
