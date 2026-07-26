#!/usr/bin/env bash
# UserPromptSubmit hook: blocks prompts that appear to contain credentials
# Exit 2 hard-blocks the prompt; exit 0 allows it through.
#
# Fast path: bash-only regex extract of the prompt (no jq for the common case
# of a plain prompt), then a single alternation grep as a cheap reject filter.
# Only if the alternation matches do we run the per-pattern greps to label
# what was found.
#
# After stowing, make executable: chmod +x ~/.claude/hooks/secret-scan.sh
set -uo pipefail

INPUT=$(cat)

# Try bash-only extraction first. If the prompt contains embedded double quotes
# or JSON control characters, fall back to jq for correctness.
if [[ "$INPUT" =~ \"prompt\"[[:space:]]*:[[:space:]]*\"([^\"\\]*)\" ]]; then
  PROMPT="${BASH_REMATCH[1]}"
else
  PROMPT=$(printf '%s' "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)
fi

[[ -z "$PROMPT" ]] && exit 0

# One alternation pass rejects ~99% of prompts without spawning per-pattern greps.
if ! echo "$PROMPT" | grep -qE 'sk-[a-zA-Z0-9]{20,}|gh[poas]_[a-zA-Z0-9]{36,}|AKIA[A-Z0-9]{16}|xox[bpsa]-[a-zA-Z0-9-]+|AIza[0-9A-Za-z_-]{35}|-----BEGIN'; then
  exit 0
fi

HOOK="[hook: secret-scan]"
LOG="$HOME/.claude/hooks/hook-debug.log"
DETECTED=()

# Something matched — now label which patterns hit for a useful error message.
echo "$PROMPT" | grep -qE 'sk-[a-zA-Z0-9]{20,}'           && DETECTED+=("OpenAI API key")
echo "$PROMPT" | grep -qE 'gh[poas]_[a-zA-Z0-9]{36,}'     && DETECTED+=("GitHub token")
echo "$PROMPT" | grep -qE 'AKIA[A-Z0-9]{16}'              && DETECTED+=("AWS access key")
echo "$PROMPT" | grep -qE 'xox[bpsa]-[a-zA-Z0-9-]+'       && DETECTED+=("Slack token")
echo "$PROMPT" | grep -qE 'AIza[0-9A-Za-z_-]{35}'         && DETECTED+=("Google API key")
echo "$PROMPT" | grep -qF '-----BEGIN'                    && DETECTED+=("private key")

LABELS=$(IFS=', '; echo "${DETECTED[*]}")
echo "$(date -u +%FT%TZ) $HOOK BLOCKED: $LABELS" >> "$LOG"
echo "$HOOK BLOCKED: Prompt appears to contain credentials: $LABELS"
echo "Remove credentials before submitting. Use environment variables or a secrets manager instead."
exit 2
