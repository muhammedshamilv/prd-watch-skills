#!/usr/bin/env bash
# Daily PRD drift check (Confluence only). Run from cron; writes reports to ~/prd-watch/<feature>/reports/.
# Figma is checked on demand with the figma-watch skill, never from here.
# Read-only: the scheduled run can never edit Confluence (RFC updates happen only in /prd-watch rfc-update, with user confirmation).
#
# Cost control:
#   1. A Haiku pre-check fetches only the current version numbers. If no PRD or RFC moved,
#      precheck.py writes the short report itself and the full run is skipped.
#   2. The full check runs on Sonnet (override with PRD_WATCH_MODEL).
set -uo pipefail
export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"
BASE="$HOME/prd-watch"
LOG="$BASE/cron.log"
SCRIPTS="$HOME/.claude/skills/prd-watch/scripts"
CLAUDE="${CLAUDE_BIN:-$(command -v claude || echo "$HOME/.local/bin/claude")}"
MODEL="${PRD_WATCH_MODEL:-sonnet}"
PRECHECK_MODEL="${PRD_WATCH_PRECHECK_MODEL:-haiku}"
GET="mcp__claude_ai_Atlassian_MCP__getConfluenceContent"
mkdir -p "$BASE"
cd "$BASE"

full_check() {
  "$CLAUDE" -p "/prd-watch check $1" --model "$MODEL" \
    --allowedTools "$GET" "mcp__claude_ai_Atlassian_MCP__executeRead" "mcp__claude_ai_Atlassian_MCP__discover" "mcp__claude_ai_Atlassian_MCP__getPeopleInfo" "mcp__claude_ai_Atlassian_MCP__getAccessibleAtlassianResources" \
      "Read" "Write" "Edit" "ToolSearch" "Skill" \
      "Bash(python3 -I $SCRIPTS/prd_diff.py:*)" \
      "Bash(mkdir:*)" "Bash(date:*)" "Bash(ls:*)" "Bash(cat:*)" </dev/null
}

{
  echo "=== $(date -Is) ==="
  for meta in "$BASE"/*/meta.json; do
    [ -e "$meta" ] || continue
    fdir="$(dirname "$meta")"
    feature="$(basename "$fdir")"
    read -r cloud pages < <(python3 -I "$SCRIPTS/precheck.py" ids "$fdir")
    versions="$(mktemp)"
    "$CLAUDE" -p "Load the tool $GET with ToolSearch (query \"select:$GET\"). For each Confluence page id below, call it with cloudId=\"$cloud\", contentId=<id>, detail=\"summary\", and read metadata.version.number. Page ids: $pages. Reply with exactly one line of JSON mapping each page id (string) to its version number (integer), for example {\"123\": 4}. If any call fails, reply {\"error\": \"<short reason>\"}. Do nothing else." \
      --model "$PRECHECK_MODEL" --allowedTools "ToolSearch" "$GET" </dev/null >"$versions" 2>&1
    if python3 -I "$SCRIPTS/precheck.py" compare "$fdir" "$versions"; then
      echo "[$feature] pre-check ($PRECHECK_MODEL): no PRD/RFC edits; full run skipped. $(tail -n1 "$versions")"
    else
      echo "[$feature] pre-check ($PRECHECK_MODEL): change or unknown -> full check on $MODEL. Pre-check said: $(tail -n1 "$versions")"
      if full_check "$feature"; then
        python3 -I "$SCRIPTS/precheck.py" save "$fdir" "$versions"
      fi
    fi
    rm -f "$versions"
  done
} >>"$LOG" 2>&1
