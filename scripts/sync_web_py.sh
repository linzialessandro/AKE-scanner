#!/usr/bin/env bash
# Copy pure-Python package + examples into docs/py for GitHub Pages / Pyodide.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/docs/py"

rm -rf "$DEST"
mkdir -p "$DEST/ake_scanner" "$DEST/examples"

# Package (no bytecode, no egg-info)
rsync -a --exclude '__pycache__' --exclude '*.pyc' --exclude '*.egg-info' \
  "$ROOT/src/ake_scanner/" "$DEST/ake_scanner/"

rsync -a --exclude '__pycache__' --exclude '*.pyc' \
  "$ROOT/examples/" "$DEST/examples/"

# Marker so the web app can confirm vendor presence
cat > "$DEST/README.txt" << 'MARK'
Vendored copy of ake_scanner + examples for the GitHub Pages UI.
Regenerate with: scripts/sync_web_py.sh
Do not edit by hand.
MARK

echo "Synced → docs/py ($(find "$DEST" -name '*.py' | wc -l | tr -d ' ') python files)"
