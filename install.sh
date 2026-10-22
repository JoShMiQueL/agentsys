#!/usr/bin/env sh
# install.sh — agentsys installer for Linux/macOS
# Remote: curl -fsSL https://raw.githubusercontent.com/JoShMiQueL/agentsys/master/install.sh | sh
# Local:  sh install.sh [systems...]
set -e
REPO='JoShMiQueL/agentsys'
DEST="${AGENTSYS_HOME:-$HOME/.agentsys}"
SYSTEMS="${*:-general}"

command -v curl  >/dev/null || { echo "curl required"; exit 1; }
command -v unzip >/dev/null || { echo "unzip required"; exit 1; }

if [ -d "$(dirname "$0")/systems" ]; then
  DEST_DIR="$(cd "$(dirname "$0")" && pwd)"   # local run inside repo
else
  TAG=$(curl -fsSL "https://api.github.com/repos/$REPO/tags" | grep -m1 '"name"' | sed 's/.*"name": *"\([^"]*\)".*/\1/')
  REF=${TAG:-master}
  echo "downloading $REPO @ $REF -> $DEST"
  rm -rf "$DEST"; mkdir -p "$DEST"
  curl -fsSL "https://github.com/$REPO/archive/$REF.zip" -o /tmp/agentsys.zip
  (cd /tmp && unzip -oq agentsys.zip && cp -R agentsys-*/. "$DEST"/ && rm -rf agentsys-* agentsys.zip)
  [ -n "$TAG" ] && echo "$TAG" > "$DEST/VERSION"
  chmod +x "$DEST/bin/agentsys" 2>/dev/null || true
  DEST_DIR="$DEST"
fi

# deps (best effort — ollama/python may need manual install per distro)
for c in python3 ollama; do
  command -v $c >/dev/null || echo "  [warn] $c not found — install it for models/CLI to work"
done
command -v python3 >/dev/null || exit 1

# PATH registration
line='export PATH="$HOME/.agentsys/bin:$PATH"'
for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
  [ -f "$rc" ] && ! grep -q '.agentsys/bin' "$rc" 2>/dev/null && { echo "$line" >> "$rc"; echo "added PATH to $rc"; }
done

# shellcheck disable=SC2086
python3 "$DEST_DIR/cli.py" install $SYSTEMS
echo ""
echo "Done. Restart your shell, then: agentsys doctor"
