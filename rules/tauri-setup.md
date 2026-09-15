# Tauri Development Environment Setup

Tauri apps fail to build for reasons that have nothing to do with the app's code — a missing system webview package, an unpinned Rust toolchain, or a Node version mismatch. Diagnosing that mid-build wastes a cycle that a five-second prerequisite check would have caught. This rule is the single source of truth for detecting and installing Tauri's dependencies; `skills/tauri/SKILL.md` invokes it, it does not restate it.

Source: https://v2.tauri.app/start/prerequisites/ — verify against the live page if a package name below appears stale (webview package names have changed across Tauri v1 → v2).

## Recognition Signals — what's missing and how to install it

| Signal (command exits non-zero or binary absent) | Platform | Install command |
|---|---|---|
| `rustc --version` fails | All | `curl --proto '=https' --tlsv1.2 https://sh.rustup.rs -sSf \| sh` then restart the shell, or `rustup update` if already installed but stale |
| `node --version` fails (only needed if the frontend is JS/TS) | All | Install Node LTS from nodejs.org, or via a version manager (`fnm`, `nvm`, `mise`) the project already uses — check for `.nvmrc` / `.node-version` first |
| `xcode-select -p` fails | macOS | `xcode-select --install` (desktop-only). Full Xcode from the App Store is required only for iOS targets |
| `pkg-config --exists webkit2gtk-4.1` fails | Debian/Ubuntu | `sudo apt update && sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget file libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev` |
| same, on Arch | Arch | `sudo pacman -S --needed webkit2gtk-4.1 base-devel curl wget file openssl appmenu-gtk-module libappindicator-gtk3 librsvg xdotool` |
| same, on Fedora | Fedora | `sudo dnf install webkit2gtk4.1-devel openssl-devel curl wget file libappindicator-gtk3-devel librsvg2-devel libxdo-devel && sudo dnf group install "c-development"` |
| same, on Alpine | Alpine | `sudo apk add build-base webkit2gtk-4.1-dev curl wget file openssl libayatana-appindicator-dev librsvg` — Alpine containers also need at least one font package (`font-dejavu`) or in-app text renders blank |
| MSVC linker errors / "link.exe not found" | Windows | Install "Microsoft C++ Build Tools" from visualstudio.microsoft.com, selecting **Desktop development with C++** |
| WebView2 missing (Windows versions before Windows 10 1803) | Windows | Download the Evergreen Bootstrapper from developer.microsoft.com/microsoft-edge/webview2/ — skip on current Windows 10/11, it ships in-box |
| MSI bundler fails referencing VBSCRIPT | Windows | Settings → Apps → Optional Features → More Windows features → enable **VBSCRIPT**, then restart |
| `rustup target list --installed` missing `aarch64-apple-ios` / `*-android` targets | Mobile (iOS/Android) | See Mobile targets below — only required if the app targets mobile |

## Mandatory Behaviors

**Always run the detection script before scaffolding or building.** Do not ask the user to eyeball their toolchain — run:

```bash
bash ~/.claude/skills/tauri/check_prereqs.sh
```

It prints exactly what's missing and the exact install command for the detected OS/distro, and exits `0` when nothing is missing, `1` otherwise. Never re-run a full install pass when the script reports everything present.

**Confirm before running any command that installs system-wide packages.** `sudo apt install`, `sudo dnf install`, `sudo pacman -S`, `sudo apk add`, and Windows installers modify shared machine state outside the project — per the standing "Executing actions with care" guidance, state the exact command and get explicit confirmation before running it. `rustup`, `cargo install --locked`, and user-scoped `npm`/`pnpm`/`yarn` installs do not touch system state and do not require this extra confirmation.

**Use a pinned, package-manager-based project scaffold — never the raw installer script.** `sh <(curl https://create.tauri.app/sh)` is a `curl | sh` supply-chain pattern (`rules/owasp-top-10.md` A03). Use one of the pinned equivalents instead:

```bash
npm create tauri-app@latest
pnpm create tauri-app
yarn create tauri-app
cargo install create-tauri-app --locked   # then: create-tauri-app
```

Prefer whichever package manager the project (or the user) already uses; detect via lockfile (`pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`) before defaulting to `npm`.

**Verify webview package naming for the Tauri major version in use.** Tauri v2 uses `webkit2gtk-4.1` / `libwebkit2gtk-4.1-dev`; v1 tutorials reference the now-superseded `4.0` packages. Check `src-tauri/Cargo.toml`'s `tauri` dependency version before copying an install command from an older doc or Stack Overflow answer.

**Mobile targets are opt-in — do not install Android/iOS toolchains for a desktop-only app.** Only run the mobile setup below when the user has asked for an Android or iOS target.

### Mobile targets (only when requested)

**iOS (macOS host only):**

```bash
rustup target add aarch64-apple-ios x86_64-apple-ios aarch64-apple-ios-sim
brew install cocoapods   # requires Homebrew; confirm before installing Homebrew itself if absent
```

**Android (any host):**

```bash
rustup target add aarch64-linux-android armv7-linux-androideabi i686-linux-android x86_64-linux-android
```

Requires Android Studio + NDK installed separately, plus `JAVA_HOME`, `ANDROID_HOME`, and `NDK_HOME` exported (paths differ by OS — see https://v2.tauri.app/start/prerequisites/#android for the exact per-OS paths). Confirm the user wants mobile support before walking through this — it is a materially heavier setup than desktop-only.

## Pragmatism Guard

Do not apply this rule when:

- **The project already has a working `src-tauri/` and `cargo build` / `pnpm tauri dev` already succeeds.** Re-checking prerequisites on every invocation is wasted work — only run the check on first scaffold, after a reported build failure that matches a signal above, or when explicitly asked.
- **Running inside a container image that already declares these system packages** (a `Dockerfile` with `apt-get install` lines covering the same packages). Trust the image; do not re-install inside it.
- **The user has explicitly said their environment is already set up.** Skip the check; if the build then fails on a missing-dependency signal, run the check at that point instead of pre-emptively.

## Anti-Patterns to Avoid

- **Running `curl | sh` for the project scaffold.** Use the pinned package-manager form instead — see Mandatory Behaviors above.
- **Installing system packages without stating the command and getting confirmation first.** A `sudo apt install` a user didn't expect is a bigger surprise than the five seconds it costs to ask.
- **Copying v1-era `webkit2gtk-4.0` package names into a v2 project.** Check the Tauri version in `Cargo.toml` first.
- **Blanket-installing mobile toolchains "just in case."** Desktop-only apps never need `ANDROID_HOME` or CocoaPods — only set them up when a mobile target is explicitly requested.
