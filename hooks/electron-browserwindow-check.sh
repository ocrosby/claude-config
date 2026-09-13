#!/usr/bin/env bash
# PreToolUse hook: warns before Edit/Write introduces an insecure BrowserWindow
# option or a contextBridge that exposes ipcRenderer directly.
#
# Exit 2 hard-blocks the tool call (loud warning; user can override on next try).
# Exit 0 allows it through.
#
# Reads the JSON tool call on stdin, extracts the string that will be written
# (Write.content or Edit.new_string), and scans it for the most severe
# recognition signals from rules/electron-security.md.
#
# After stowing, make executable: chmod +x ~/.claude/hooks/electron-browserwindow-check.sh
set -uo pipefail

INPUT=$(cat)

# jq is standard on developer machines; if absent we skip the check silently rather than blocking.
if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)

# Only inspect Edit and Write payloads; MultiEdit is out of scope for this cheap hook.
case "$TOOL" in
  Edit)  PAYLOAD=$(printf '%s' "$INPUT" | jq -r '.tool_input.new_string // empty' 2>/dev/null) ;;
  Write) PAYLOAD=$(printf '%s' "$INPUT" | jq -r '.tool_input.content // empty' 2>/dev/null) ;;
  *) exit 0 ;;
esac

FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

# Only fire on JS/TS-shaped files; forge/builder configs also count.
case "$FILE_PATH" in
  *.js|*.ts|*.cjs|*.mjs|*.jsx|*.tsx|*forge.config*|*electron-builder*) ;;
  *) exit 0 ;;
esac

[[ -z "$PAYLOAD" ]] && exit 0

HOOK="[hook: electron-browserwindow-check]"
LOG="$HOME/.claude/hooks/hook-debug.log"
DETECTED=()

# Alternation rejects ~all non-Electron edits cheaply.
if ! echo "$PAYLOAD" | grep -qE 'nodeIntegration|contextIsolation|webSecurity|sandbox|allowRunningInsecureContent|experimentalFeatures|enableBlinkFeatures|exposeInMainWorld|@electron/remote'; then
  exit 0
fi

echo "$PAYLOAD" | grep -qE 'nodeIntegration[[:space:]]*:[[:space:]]*true'                 && DETECTED+=("nodeIntegration: true")
echo "$PAYLOAD" | grep -qE 'contextIsolation[[:space:]]*:[[:space:]]*false'               && DETECTED+=("contextIsolation: false")
echo "$PAYLOAD" | grep -qE 'webSecurity[[:space:]]*:[[:space:]]*false'                    && DETECTED+=("webSecurity: false")
echo "$PAYLOAD" | grep -qE 'allowRunningInsecureContent[[:space:]]*:[[:space:]]*true'     && DETECTED+=("allowRunningInsecureContent: true")
echo "$PAYLOAD" | grep -qE 'experimentalFeatures[[:space:]]*:[[:space:]]*true'            && DETECTED+=("experimentalFeatures: true")
echo "$PAYLOAD" | grep -qE 'enableBlinkFeatures[[:space:]]*:'                             && DETECTED+=("enableBlinkFeatures set")
echo "$PAYLOAD" | grep -qE 'exposeInMainWorld\([^,]*,[[:space:]]*ipcRenderer'             && DETECTED+=("contextBridge exposes ipcRenderer directly")
echo "$PAYLOAD" | grep -qE "require\\(['\"]@electron/remote['\"]\\)|from[[:space:]]+['\"]@electron/remote['\"]" && DETECTED+=("@electron/remote import")

if [[ ${#DETECTED[@]} -eq 0 ]]; then
  exit 0
fi

LABELS=$(IFS=', '; echo "${DETECTED[*]}")
echo "$(date -u +%FT%TZ) $HOOK BLOCKED on $FILE_PATH: $LABELS" >> "$LOG"
echo "$HOOK BLOCKED on $FILE_PATH"
echo "The edit would introduce Electron security regressions: $LABELS"
echo "See rules/electron-security.md § Recognition Signals — every entry above is Must Fix."
echo "If the deviation is intentional, add an inline comment naming the specific threat model and retry."
exit 2
