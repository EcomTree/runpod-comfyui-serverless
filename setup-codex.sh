#!/bin/bash

# Compatibility wrapper for the legacy Codex setup entrypoint.
# The optimized script was renamed to setup-codex-optimized.sh.
# Keep this thin shim so existing Codex configurations keep working.
#
# NOTE: This script is NOT designed for piped execution (curl | bash).
# For piped execution, use setup-codex-optimized.sh directly:
#   curl -fsSL https://raw.githubusercontent.com/.../setup-codex-optimized.sh | bash

# Detect script directory - only works when script is saved to disk
if [[ -n "${BASH_SOURCE[0]:-}" && "${BASH_SOURCE[0]}" != "bash" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
    # Fallback: assume we're in the repository root (or piped execution)
    SCRIPT_DIR="$(pwd)"
fi

TARGET_SCRIPT="${SCRIPT_DIR}/setup-codex-optimized.sh"

if [[ ! -f "${TARGET_SCRIPT}" ]]; then
    echo "❌ setup-codex-optimized.sh not found (path: ${TARGET_SCRIPT})" >&2
    echo "➡️  Please re-clone the repository or pull the latest release." >&2
    echo "➡️  Or use the optimized script directly for piped execution:" >&2
    echo "    curl -fsSL https://raw.githubusercontent.com/EcomTree/runpod-comfyui-serverless/main/setup-codex-optimized.sh | bash" >&2
    exit 1
fi

exec "${TARGET_SCRIPT}" "$@"

