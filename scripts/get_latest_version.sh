#!/usr/bin/env bash
set -euo pipefail

# get_latest_version.sh
# Prints the latest ComfyUI release tag to stdout.
# Fallbacks to the latest annotated tag, or main if none.
# Optional env:
#   GITHUB_TOKEN - increases rate limits (optional)
#   REPO         - override repository (default: comfyanonymous/ComfyUI)

REPO="${REPO:-comfyanonymous/ComfyUI}"
API_URL="https://api.github.com/repos/${REPO}/releases/latest"

auth_header=()
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
  auth_header=(-H "Authorization: token ${GITHUB_TOKEN}")
fi

get_latest_release() {
  # Try to fetch the latest release tag_name
  if command -v curl >/dev/null 2>&1; then
    set +e
    response=$(curl -sS "${auth_header[@]}" "${API_URL}")
    status=$?
    set -e
    if [[ $status -eq 0 ]]; then
      tag=$(printf '%s' "$response" | sed -n 's/.*"tag_name"\s*:\s*"\([^"]\+\)".*/\1/p' | head -n1)
      if [[ -n "$tag" ]]; then
        printf '%s' "$tag"
        return 0
      fi
    fi
  fi
  return 1
}

get_latest_tag_via_git() {
  tmpdir=$(mktemp -d)
  trap 'rm -rf "$tmpdir"' EXIT
  git -c advice.detachedHead=false clone --depth=1 --filter=blob:none "https://github.com/${REPO}.git" "$tmpdir/repo" >/dev/null 2>&1 || return 1
  pushd "$tmpdir/repo" >/dev/null 2>&1
  # Fetch tags (lightweight and annotated) shallowly
  git fetch --tags --depth=1 >/dev/null 2>&1 || true
  # Prefer tags that look like versions and sort semver-ish
  latest=$(git tag --list | grep -E '^v?[0-9]+(\.[0-9]+)*' | sort -V | tail -n1)
  if [[ -z "$latest" ]]; then
    latest=$(git tag --list | sort -V | tail -n1)
  fi
  if [[ -n "$latest" ]]; then
    printf '%s' "$latest"
    popd >/dev/null 2>&1
    return 0
  fi
  popd >/dev/null 2>&1
  return 1
}

main() {
  if latest=$(get_latest_release); then
    printf '%s' "$latest"
    exit 0
  fi
  if latest=$(get_latest_tag_via_git); then
    printf '%s' "$latest"
    exit 0
  fi
  # Last resort, use main
  printf '%s' "main"
}

main "$@"
