#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE=${1:-/workspace/configs/custom_nodes.json}
INSTALL_ROOT=""

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Config not found: $CONFIG_FILE" >&2
  exit 1
fi

# Read install_root and nodes via Python (portable, no jq dependency)
read_config() {
  python3 - "$CONFIG_FILE" << 'PY'
import json, sys, os
path = sys.argv[1]
with open(path, 'r') as f:
    data = json.load(f)
root = data.get('install_root') or '/workspace/ComfyUI/custom_nodes'
nodes = data.get('nodes', [])
print(root)
for n in nodes:
    name = n.get('name')
    repo = n.get('repo')
    install_reqs = bool(n.get('install_requirements', True))
    if name and repo:
        print("NODE\t%s\t%s\t%s" % (name, repo, '1' if install_reqs else '0'))
PY
}

mapfile -t LINES < <(read_config)
INSTALL_ROOT="${LINES[0]}"
mkdir -p "$INSTALL_ROOT"

echo "Installing custom nodes into: $INSTALL_ROOT"

for ((i=1; i<${#LINES[@]}; i++)); do
  IFS=$'\t' read -r marker name repo install_reqs <<< "${LINES[$i]}"
  [[ "$marker" == "NODE" ]] || continue
  dest="$INSTALL_ROOT/$name"
  if [[ -d "$dest/.git" ]]; then
    echo "⤴️  Updating $name"
    git -C "$dest" pull --ff-only || true
  elif [[ -d "$dest" ]]; then
    echo "📁 Reusing existing directory for $name"
  else
    echo "⬇️  Cloning $name from $repo"
    git clone --filter=blob:none "$repo" "$dest"
  fi
  # Install requirements if present
  if [[ "$install_reqs" == "1" ]]; then
    if [[ -f "$dest/requirements.txt" ]]; then
      echo "📦 Installing requirements for $name"
      pip install --no-cache-dir -r "$dest/requirements.txt"
    fi
    if [[ -f "$dest/requirements-dev.txt" ]]; then
      pip install --no-cache-dir -r "$dest/requirements-dev.txt" || true
    fi
  fi
  # Optional build steps
  if [[ -f "$dest/build.sh" ]]; then
    echo "🏗️  Running build.sh for $name"
    bash "$dest/build.sh" || true
  fi
done

echo "✅ Custom nodes installation finished"
