#!/usr/bin/env bash
# Fast Electron security scanner — emits a Markdown report of the most severe
# BrowserWindow / preload / contextBridge misconfigurations under <repo-root>.
#
# Exit codes:
#   0 — no severe signals found
#   1 — one or more severe signals found (Must Fix per rules/electron-security.md)
#   2 — usage error
#
# Called by /electron audit before delegating to electron-reviewer.
set -uo pipefail

ROOT="${1:-.}"
if [[ ! -d "$ROOT" ]]; then
  echo "usage: scan_insecure.sh <repo-root>" >&2
  exit 2
fi

# rg is standard on developer machines; fall back to grep -r if absent.
if command -v rg >/dev/null 2>&1; then
  RG=(rg --no-heading --line-number --color=never --glob '!node_modules' --glob '!dist' --glob '!out' --glob '!.git' --glob '*.{js,ts,cjs,mjs,jsx,tsx}')
else
  RG=(grep -rn --include='*.js' --include='*.ts' --include='*.cjs' --include='*.mjs' --include='*.jsx' --include='*.tsx' --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=out --exclude-dir=.git)
fi

hits=0
report() {
  local label="$1"; shift
  local pattern="$1"; shift
  local out
  out=$("${RG[@]}" -e "$pattern" "$ROOT" 2>/dev/null || true)
  if [[ -n "$out" ]]; then
    hits=$((hits + 1))
    echo
    echo "### $label"
    echo
    echo '```'
    echo "$out"
    echo '```'
  fi
}

echo "# Electron security scan"
echo
echo "Root: \`$ROOT\`"
echo
echo "Severe recognition signals from rules/electron-security.md:"

report "nodeIntegration enabled" 'nodeIntegration[[:space:]]*:[[:space:]]*true'
report "contextIsolation disabled" 'contextIsolation[[:space:]]*:[[:space:]]*false'
report "webSecurity disabled" 'webSecurity[[:space:]]*:[[:space:]]*false'
report "sandbox explicitly disabled" 'sandbox[[:space:]]*:[[:space:]]*false'
report "allowRunningInsecureContent enabled" 'allowRunningInsecureContent[[:space:]]*:[[:space:]]*true'
report "experimentalFeatures enabled" 'experimentalFeatures[[:space:]]*:[[:space:]]*true'
report "enableBlinkFeatures set" 'enableBlinkFeatures[[:space:]]*:'
report "contextBridge exposing ipcRenderer directly" 'exposeInMainWorld\([^,]*,[[:space:]]*ipcRenderer'
report "contextBridge object literal containing ipcRenderer" 'exposeInMainWorld\([^)]*ipcRenderer'
report "@electron/remote usage (deprecated)" "require\\(['\"]@electron/remote['\"]\\)|from[[:space:]]+['\"]@electron/remote['\"]"
report "shell.openExternal called without an obvious allowlist" 'shell\.openExternal\('

echo
if [[ $hits -eq 0 ]]; then
  echo "**Result:** no severe signals matched. Full checklist still needs the electron-reviewer agent."
  exit 0
else
  echo "**Result:** $hits severe signal category/categories matched. Each is Must Fix per rules/electron-security.md."
  exit 1
fi
