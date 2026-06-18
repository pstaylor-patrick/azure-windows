#!/usr/bin/env bash
# Install (or uninstall) the awvm Claude Code skills by symlinking
# skills/*.md into ~/.claude/commands/.
#
# Mirrors the pattern used in ~/workspaces/growth/repos/skills/install.sh
# — Claude Code only, no Codex / Pi.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$REPO_DIR/skills"
CLAUDE_COMMANDS_DIR="$HOME/.claude/commands"

SKILLS=(
  "awvm"
  "awvm-up"
  "awvm-down"
  "awvm-connect"
  "awvm-status"
  "awvm-refresh-ip"
)

UNINSTALL=false
LAUNCHD_CMD=""

LAUNCHD_DIR="$HOME/Library/LaunchAgents"
REAPER_PLIST="$LAUNCHD_DIR/com.awvm.reaper.plist"
SMOKE_PLIST="$LAUNCHD_DIR/com.awvm.smoke-test.plist"

usage() {
  cat <<'EOF'
Usage: ./install.sh [--uninstall] [--load-launchd] [--unload-launchd] [-h|--help]

Installs (or uninstalls) the awvm Claude Code skills by symlinking
each skills/*.md file into ~/.claude/commands/.

Options:
  --uninstall       Remove the skill symlinks instead of creating them
  --load-launchd    Install and load the reaper + smoke-test launchd agents
  --unload-launchd  Unload and remove the reaper + smoke-test launchd agents
  -h, --help        Show this message
EOF
}

for arg in "$@"; do
  case "$arg" in
    --uninstall)      UNINSTALL=true ;;
    --load-launchd)   LAUNCHD_CMD=load ;;
    --unload-launchd) LAUNCHD_CMD=unload ;;
    --help|-h)        usage; exit 0 ;;
    *)
      echo "Unknown argument: $arg" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "$LAUNCHD_CMD" == "load" ]]; then
  mkdir -p "$LAUNCHD_DIR"
  cp "$REPO_DIR/launchd/com.awvm.reaper.plist" "$REAPER_PLIST"
  cp "$REPO_DIR/launchd/com.awvm.smoke-test.plist" "$SMOKE_PLIST"
  launchctl load "$REAPER_PLIST"
  launchctl load "$SMOKE_PLIST"
  echo "launchd agents loaded (reaper every 15 min, smoke-test at 6am Mon-Fri)."
  exit 0
fi

if [[ "$LAUNCHD_CMD" == "unload" ]]; then
  launchctl unload "$REAPER_PLIST" 2>/dev/null || true
  launchctl unload "$SMOKE_PLIST" 2>/dev/null || true
  rm -f "$REAPER_PLIST" "$SMOKE_PLIST"
  echo "launchd agents unloaded."
  exit 0
fi

if [[ "$UNINSTALL" == true ]]; then
  for skill in "${SKILLS[@]}"; do
    dst="$CLAUDE_COMMANDS_DIR/$skill.md"
    if [[ -L "$dst" ]]; then
      rm "$dst"
      echo "Uninstalled /$skill (removed $dst)"
    elif [[ -e "$dst" ]]; then
      echo "Skipped /$skill: $dst exists but is not a symlink"
    fi
  done
  exit 0
fi

mkdir -p "$CLAUDE_COMMANDS_DIR"

for skill in "${SKILLS[@]}"; do
  src="$SKILLS_DIR/$skill.md"
  dst="$CLAUDE_COMMANDS_DIR/$skill.md"
  if [[ ! -f "$src" ]]; then
    echo "WARNING: $src does not exist, skipping" >&2
    continue
  fi
  ln -sfn "$src" "$dst"
  echo "Installed /$skill -> $src"
done

echo ""
echo "Done. ${#SKILLS[@]} skills installed to $CLAUDE_COMMANDS_DIR/"
echo "Try: /awvm, /awvm-up, /awvm-down, /awvm-connect, /awvm-status, /awvm-refresh-ip"
echo ""
echo "To enable the reaper + smoke-test scheduler: ./install.sh --load-launchd"
