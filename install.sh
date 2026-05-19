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

usage() {
  cat <<'EOF'
Usage: ./install.sh [--uninstall] [-h|--help]

Installs (or uninstalls) the awvm Claude Code skills by symlinking
each skills/*.md file into ~/.claude/commands/.

Options:
  --uninstall  Remove the symlinks instead of creating them
  -h, --help   Show this message
EOF
}

for arg in "$@"; do
  case "$arg" in
    --uninstall) UNINSTALL=true ;;
    --help|-h)   usage; exit 0 ;;
    *)
      echo "Unknown argument: $arg" >&2
      usage >&2
      exit 1
      ;;
  esac
done

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
