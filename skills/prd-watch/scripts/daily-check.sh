#!/usr/bin/env bash
# Daily PRD drift check (Confluence only). Run from cron; writes reports to ~/prd-watch/<feature>/reports/.
# Figma is checked on demand with the figma-watch skill, never from here.
# Read-only: the scheduled run can never edit Confluence (RFC updates happen only in /prd-watch rfc-update, with user confirmation).
set -euo pipefail
export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"
LOG="$HOME/prd-watch/cron.log"
mkdir -p "$HOME/prd-watch"
cd "$HOME/prd-watch"

{
  echo "=== $(date -Is) ==="
  "${CLAUDE_BIN:-$(command -v claude || echo "$HOME/.local/bin/claude")}" -p "/prd-watch check all" \
    --allowedTools "mcp__claude_ai_Atlassian_MCP__getConfluenceContent" "mcp__claude_ai_Atlassian_MCP__executeRead" "mcp__claude_ai_Atlassian_MCP__discover" "mcp__claude_ai_Atlassian_MCP__getPeopleInfo" "mcp__claude_ai_Atlassian_MCP__getAccessibleAtlassianResources" \
      "Read" "Write" "Edit" "ToolSearch" "Skill" \
      "Bash(python3 -I $HOME/.claude/skills/prd-watch/scripts/prd_diff.py:*)" \
      "Bash(mkdir:*)" "Bash(date:*)" "Bash(ls:*)" "Bash(cat:*)"
} >>"$LOG" 2>&1
