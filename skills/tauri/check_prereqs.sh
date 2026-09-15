#!/usr/bin/env bash
# check_prereqs.sh — detect missing Tauri v2 build dependencies for the
# current OS/distro and print the exact install command for each gap.
#
# Usage:
#   check_prereqs.sh              # check desktop-only prerequisites
#   check_prereqs.sh --mobile      # also check Android/iOS rustup targets
#
# Output: Markdown to stdout.
# Exit code: 0 if nothing is missing, 1 if anything is missing.
#
# Full command reference: rules/tauri-setup.md

set -euo pipefail

MOBILE=0
if [ "${1-}" = "--mobile" ]; then
  MOBILE=1
fi

missing=0
report=()

add_missing() {
  missing=1
  report+=("- **Missing:** $1")
  report+=("  **Install:** \`$2\`")
}

have() {
  command -v "$1" >/dev/null 2>&1
}

OS="$(uname -s)"

echo "## Tauri prerequisite check ($OS)"
echo

# --- Rust toolchain (all platforms) ---
if ! have rustc || ! have cargo; then
  add_missing "Rust toolchain (rustc/cargo)" "curl --proto '=https' --tlsv1.2 https://sh.rustup.rs -sSf | sh"
else
  echo "- rustc: $(rustc --version)"
fi

# --- Node.js (only relevant if the frontend is JS/TS; report, don't block) ---
if ! have node; then
  echo "- node: not found (only required if the frontend is JS/TS — install Node LTS from nodejs.org, or via the project's existing version manager)"
else
  echo "- node: $(node --version)"
fi

case "$OS" in
Darwin)
  if ! xcode-select -p >/dev/null 2>&1; then
    add_missing "Xcode Command Line Tools" "xcode-select --install"
  else
    echo "- Xcode Command Line Tools: present"
  fi
  if [ "$MOBILE" -eq 1 ]; then
    if ! rustup target list --installed 2>/dev/null | grep -q "aarch64-apple-ios"; then
      add_missing "iOS rustup targets" "rustup target add aarch64-apple-ios x86_64-apple-ios aarch64-apple-ios-sim"
    fi
    if ! have pod; then
      add_missing "CocoaPods" "brew install cocoapods"
    fi
  fi
  ;;
Linux)
  DISTRO_ID="unknown"
  if [ -f /etc/os-release ]; then
    DISTRO_ID="$(. /etc/os-release && echo "$ID")"
  fi

  if have pkg-config && pkg-config --exists webkit2gtk-4.1 2>/dev/null; then
    echo "- webkit2gtk-4.1: present"
  else
    case "$DISTRO_ID" in
    ubuntu | debian)
      add_missing "libwebkit2gtk-4.1-dev and build deps" "sudo apt update && sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget file libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev"
      ;;
    arch)
      add_missing "webkit2gtk-4.1 and build deps" "sudo pacman -S --needed webkit2gtk-4.1 base-devel curl wget file openssl appmenu-gtk-module libappindicator-gtk3 librsvg xdotool"
      ;;
    fedora)
      add_missing "webkit2gtk4.1-devel and build deps" "sudo dnf install webkit2gtk4.1-devel openssl-devel curl wget file libappindicator-gtk3-devel librsvg2-devel libxdo-devel && sudo dnf group install \"c-development\""
      ;;
    alpine)
      add_missing "webkit2gtk-4.1-dev and build deps" "sudo apk add build-base webkit2gtk-4.1-dev curl wget file openssl libayatana-appindicator-dev librsvg"
      ;;
    *)
      add_missing "webkit2gtk-4.1 dev package (unrecognized distro: $DISTRO_ID)" "see https://v2.tauri.app/start/prerequisites/ for your distro's package name"
      ;;
    esac
  fi

  if [ "$MOBILE" -eq 1 ]; then
    if ! rustup target list --installed 2>/dev/null | grep -q "aarch64-linux-android"; then
      add_missing "Android rustup targets" "rustup target add aarch64-linux-android armv7-linux-androideabi i686-linux-android x86_64-linux-android"
    fi
    if [ -z "${ANDROID_HOME-}" ]; then
      add_missing "ANDROID_HOME / JAVA_HOME / NDK_HOME env vars" "export JAVA_HOME=/opt/android-studio/jbr; export ANDROID_HOME=\$HOME/Android/Sdk; export NDK_HOME=\$ANDROID_HOME/ndk/\$(ls -1 \$ANDROID_HOME/ndk)"
    fi
  fi
  ;;
MINGW* | MSYS* | CYGWIN*)
  echo "- Windows detected from a POSIX shell — this script cannot check MSVC Build Tools, WebView2, or VBSCRIPT reliably."
  echo "  Run \`tauri info\` inside the project for an authoritative environment report, or verify manually per rules/tauri-setup.md."
  ;;
*)
  echo "- Unrecognized OS ($OS) — verify manually against https://v2.tauri.app/start/prerequisites/"
  ;;
esac

echo
if [ "$missing" -eq 0 ]; then
  echo "**Result: all detected prerequisites present.**"
else
  echo "### Gaps found"
  echo
  printf '%s\n' "${report[@]}"
  echo
  echo "**Confirm with the user before running any \`sudo\` install command above — it modifies system-wide state.**"
fi

exit "$missing"
