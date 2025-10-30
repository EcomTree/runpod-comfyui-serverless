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

# Helper function to handle grep exit status
# Returns 0 if grep succeeded or found no match (status 0 or 1)
# Returns 1 if grep had a real error (status > 1)
check_grep_status() {
  local status=$1
  if [[ $status -gt 1 ]]; then
    return 1
  fi
  return 0
}

get_latest_tag_via_git() {
  # Use git ls-remote to list remote tags without cloning
  # Temporarily disable errexit to handle "no tags found" gracefully
  set +e
  # Break pipeline into steps and check for errors
  git_output=$(git ls-remote --tags "https://github.com/${REPO}.git" 2>/dev/null)
  status=$?
  if [[ $status -ne 0 ]]; then
    set -e
    return 1
  fi
  awk_output=$(printf '%s\n' "$git_output" | awk '{print $2}')
  status=$?
  if [[ $status -ne 0 ]]; then
    set -e
    return 1
  fi
  grep_tags=$(printf '%s\n' "$awk_output" | grep -E 'refs/tags/')
  status=$?
  set -e
  check_grep_status $status || return 1
  
  set +e
  sed_tags=$(printf '%s\n' "$grep_tags" | sed 's#refs/tags/##')
  status=$?
  if [[ $status -ne 0 ]]; then
    set -e
    return 1
  fi
  tags=$(printf '%s\n' "$sed_tags" | grep -v '\^{}')
  status=$?
  set -e
  check_grep_status $status || return 1
  
  # Prefer tags that look like versions and sort semver-ish
  set +e
  latest=$(printf '%s\n' "$tags" | grep -E '^v?[0-9]+(\.[0-9]+)*' | sort -V | tail -n1)
  status=$?
  set -e
  check_grep_status $status || return 1
  
  if [[ -z "$latest" ]]; then
    set +e
    latest=$(printf '%s\n' "$tags" | sort -V | tail -n1)
    status=$?
    set -e
    check_grep_status $status || return 1
  fi
  
  if [[ -n "$latest" ]]; then
    printf '%s' "$latest"
    return 0
  fi
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
