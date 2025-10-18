#!/bin/bash

# Compatibility wrapper for the legacy Codex setup entrypoint.
# The optimized script was renamed to setup-codex-optimized.sh.
# Keep this thin shim so existing Codex configurations keep working.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-0}")" && pwd)"
TARGET_SCRIPT="${SCRIPT_DIR}/setup-codex-optimized.sh"

if [[ ! -f "${TARGET_SCRIPT}" ]]; then
    echo "❌ setup-codex-optimized.sh not found (path: ${TARGET_SCRIPT})" >&2
    echo "➡️  Please re-clone the repository or pull the latest release." >&2
    exit 1
fi

exec "${TARGET_SCRIPT}" "$@"

