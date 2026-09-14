# Electron: Packaging & Distribution Reference

Loaded on demand by `/electron package`. Covers Forge vs Builder choice, code signing, macOS notarization, Windows Authenticode, auto-updater backends, and `@electron/fuses`.

## Forge vs electron-builder

| Situation | Recommend |
|---|---|
| New project, no strong existing tooling | Electron Forge — official, `@electron/rebuild` runs automatically, opinionated defaults |
| Existing app already uses `electron-builder` and it works | Stay on Builder; migration cost > gain |
| Need publish targets Forge doesn't cover (Snap, AppImage variants) | electron-builder — broader target matrix |
| Want tight integration with `update.electronjs.org` free service | Forge — its default installer maker is Squirrel, which the service targets |
| Need `.deb` / `.rpm` / MSI + Windows Store bundling | electron-builder covers the widest set |

The tooling is not a security decision — both can produce signed, notarized, auto-updating apps. Pick one and stay.

## macOS signing + notarization

Required for auto-update on macOS. Squirrel.Mac rejects unsigned bundles silently.

### Prerequisites

- Apple Developer Program membership ($99/yr).
- **Developer ID Application** certificate installed in the keychain (or provided via file + password in CI).
- App-specific password created at appleid.apple.com for the signing Apple ID (Apple no longer accepts primary passwords via the notarization API).
- Team ID from the Apple Developer Portal.

### CI environment variables

```
APPLE_ID=you@example.com
APPLE_APP_SPECIFIC_PASSWORD=xxxx-xxxx-xxxx-xxxx   # NOT your Apple password
APPLE_TEAM_ID=ABCDE12345
CSC_LINK=…                                       # base64 or file: URL for the .p12
CSC_KEY_PASSWORD=…                               # password protecting the .p12
```

### Forge config (`forge.config.ts`)

```ts
export default {
  packagerConfig: {
    osxSign: {},                                  // uses @electron/osx-sign defaults
    osxNotarize: {
      appleId: process.env.APPLE_ID!,
      appleIdPassword: process.env.APPLE_APP_SPECIFIC_PASSWORD!,
      teamId: process.env.APPLE_TEAM_ID!,
    },
  },
  makers: [{ name: '@electron-forge/maker-squirrel', config: {} }],
};
```

### Verification

```bash
codesign --verify --deep --strict --verbose=2 "out/App.app"
spctl --assess --type execute --verbose "out/App.app"
xcrun stapler validate "out/App.app"
```

`spctl` must print `accepted (source=Notarized Developer ID)`. If it prints `rejected` or `source=Developer ID` (missing "Notarized"), the notarization step didn't run or didn't succeed.

## Windows Authenticode

Required for a clean SmartScreen experience; auto-update works without a signature but should not be shipped.

### Prerequisites

- Authenticode code-signing certificate (`.pfx`) from a CA — DigiCert, Sectigo, SSL.com, etc. EV certificates start with immediate SmartScreen reputation; OV certificates need reputation build-up.
- `.pfx` password.

### Forge Squirrel maker config

```ts
{
  name: '@electron-forge/maker-squirrel',
  config: {
    certificateFile: process.env.WIN_CSC_LINK,
    certificatePassword: process.env.WIN_CSC_KEY_PASSWORD,
  },
}
```

### Builder config

```yaml
win:
  certificateFile: ${env.WIN_CSC_LINK}
  certificatePassword: ${env.WIN_CSC_KEY_PASSWORD}
  signAndEditExecutable: true
```

## Auto-updater backend choice

| Backend | When |
|---|---|
| `autoUpdater` (built-in, Squirrel.Mac + Squirrel.Windows) | Rolling your own feed, or using `update.electronjs.org` |
| `update.electronjs.org` (free service) | Public GitHub repo + signed macOS builds + Squirrel installers — cheapest path |
| `electron-updater` (from `electron-builder`) | Already using Builder; broader server options (S3, Bintray-style, GitHub releases) |
| Self-hosted Hazel / Nuts / Nucleus | Private repos, custom rollout policies, staged releases |

### `update.electronjs.org` wiring

```ts
import { autoUpdater } from 'electron';

const server = 'https://update.electronjs.org';
const feed = `${server}/${owner}/${repo}/${process.platform}-${process.arch}/${app.getVersion()}`;
autoUpdater.setFeedURL({ url: feed });

setInterval(() => autoUpdater.checkForUpdates(), 60 * 60 * 1000);

autoUpdater.on('update-downloaded', (_e, _notes, name) => {
  // Prompt user, then autoUpdater.quitAndInstall()
});
```

### `electron-updater` wiring (Builder)

```ts
import { autoUpdater } from 'electron-updater';
autoUpdater.checkForUpdatesAndNotify();
```

Configure the feed in `electron-builder.yml`:

```yaml
publish:
  - provider: github
    owner: acme
    repo: app
```

## `@electron/fuses` — flip default-on behaviors

Fuses are compile-time flags baked into the Electron binary. Toggle after packaging via `@electron/fuses`.

Recommended for production:

```ts
import { flipFuses, FuseVersion, FuseV1Options } from '@electron/fuses';

await flipFuses(pathToApp, {
  version: FuseVersion.V1,
  resetAdHocDarwinSignature: true,
  [FuseV1Options.RunAsNode]: false,                                // disable ELECTRON_RUN_AS_NODE
  [FuseV1Options.EnableCookieEncryption]: true,
  [FuseV1Options.EnableNodeOptionsEnvironmentVariable]: false,     // ignore NODE_OPTIONS
  [FuseV1Options.EnableNodeCliInspectArguments]: false,            // block --inspect
  [FuseV1Options.EnableEmbeddedAsarIntegrityValidation]: true,
  [FuseV1Options.OnlyLoadAppFromAsar]: true,
  [FuseV1Options.LoadBrowserProcessSpecificV8Snapshot]: false,
  [FuseV1Options.GrantFileProtocolExtraPrivileges]: false,
});
```

Verify: `npx @electron/fuses read --app path/to/App.app`.

## CI pipeline shape

Matrix over `{ os: [macos-latest, windows-latest, ubuntu-latest] }`. Each job:

1. Checkout, install Node (matching Electron's Node line), install deps.
2. Build renderer (Vite/webpack) + main + preload bundles.
3. Package for the current OS via Forge / Builder.
4. Sign (in-job on macOS with keychain unlock; in-job on Windows with `.pfx`).
5. Notarize (macOS only) — this step takes 3–15 minutes; expect timeouts.
6. Upload artifact to release / feed.

Notarization can be moved to a separate job that runs on `macos-latest` after Windows/Linux builds complete, so a notarization retry doesn't block cross-platform artifacts.

## Common failure modes

| Symptom | Cause |
|---|---|
| `spctl` prints `rejected` after notarization | Notary responded successfully but staple wasn't applied — run `xcrun stapler staple App.app` |
| macOS build launches from Finder but not from `dmg` | `.dmg` needs to be signed separately with `@electron/osx-sign --identity …` |
| Auto-update `Error: Could not get code signature for running application` | macOS app not signed — auto-update requires signing |
| Windows SmartScreen still warns after signing | OV cert without reputation — takes days-to-weeks of installs to clear; EV cert clears immediately |
| Squirrel install "silently fails" on Windows | `RELEASES` file missing from feed, or version already installed |
| `NODE_MODULE_VERSION` mismatch in packaged app | `@electron/rebuild` didn't run on the CI machine (Forge runs it automatically; Builder needs a `postinstall`) |

## Cross-references

- `rules/electron-security.md` § Packaging, fuses, and distribution — the signals this checklist mitigates.
- `rules/electron-process-model.md` § Native modules — `@electron/rebuild` interaction with packaging.
