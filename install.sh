#!/usr/bin/env bash
# Install the prd-watch and figma-watch Claude Code skills.
#   ./install.sh                 install/update the skills only
#   ./install.sh --cron 10:15    also schedule the daily PRD check (local time, every day)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.claude/skills"
mkdir -p "$DEST" "$HOME/prd-watch"

for s in prd-watch figma-watch; do
  if [ -d "$DEST/$s" ]; then
    cp -r "$DEST/$s" "$DEST/$s.bak.$(date +%Y%m%d%H%M%S)"
    echo "Backed up existing $s"
  fi
  rm -rf "$DEST/$s"
  cp -r "$HERE/skills/$s" "$DEST/$s"
  echo "Installed $s -> $DEST/$s"
done
chmod +x "$DEST"/prd-watch/scripts/*.sh "$DEST"/prd-watch/scripts/*.py "$DEST"/figma-watch/scripts/*.py

if [ "${1:-}" = "--cron" ]; then
  T="${2:-10:15}"; H="${T%%:*}"; M="${T##*:}"
  LINE="$((10#$M)) $((10#$H)) * * * $DEST/prd-watch/scripts/daily-check.sh"
  ( crontab -l 2>/dev/null | grep -v 'prd-watch/scripts/daily-check.sh' || true; echo "$LINE" ) | crontab -
  echo "Scheduled daily PRD check: $LINE"
fi

command -v python3 >/dev/null || echo "WARNING: python3 not found; the helper scripts need it."
command -v claude  >/dev/null || echo "WARNING: claude CLI not on PATH; set CLAUDE_BIN for the cron job."
echo "Done. Next: in Claude Code run /mcp and connect Atlassian (and Figma if you will use figma-watch)."
