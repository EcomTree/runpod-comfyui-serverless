#!/bin/bash

# Maintenance script for RunPod ComfyUI Serverless project
# This script handles dependency installation, git operations, and project maintenance
# Based on Graphite upstream guide: https://graphite.dev/guides/git-set-upstream

set -euo pipefail

# Source common helpers
# Robustly determine the directory of this script
get_script_dir() {
    local src="${BASH_SOURCE[0]}"
    if [[ -n "$src" && -e "$src" ]]; then
        cd "$(dirname "$src")" && pwd
    elif [[ -n "$0" && -e "$0" ]]; then
        cd "$(dirname "$0")" && pwd
    else
        echo "Error: Unable to determine script directory." >&2
        exit 1
    fi
}
SCRIPT_DIR="$(get_script_dir)"

# Check if helper script exists and source it, otherwise use inline fallbacks
if [[ -f "${SCRIPT_DIR}/common-codex.sh" ]]; then
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/common-codex.sh"
else
    echo "⚠️  common-codex.sh not found, using inline fallback functions" >&2
    command_exists() { command -v "$1" >/dev/null 2>&1; }
    is_codex_environment() {
        [ -n "${CODEX_CONTAINER:-}" ] || \
        [ -n "${RUNPOD_POD_ID:-}" ] || \
        [ -n "${CODEX_WORKSPACE:-}" ] || \
        [ -d "/workspace" ]
    }
fi

# Configuration
PROJECT_NAME="runpod-comfyui-serverless"
REMOTE_URL="https://github.com/EcomTree/runpod-comfyui-serverless.git"
PYTHON_REQUIREMENTS="requirements.txt"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" >&2
}

log_error() {
    echo -e "${RED}❌ $1${NC}" >&2
}

# Check if we're in a git repository
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository. Initializing..."
        git init
        git remote add origin "$REMOTE_URL"
        log_success "Git repository initialized"
    fi
}

# Setup git remotes
setup_git_remotes() {
    log_info "Setting up git remotes..."
    
    # Check if origin exists
    if ! git remote get-url origin > /dev/null 2>&1; then
        git remote add origin "$REMOTE_URL"
        log_success "Added origin remote"
    else
        log_info "Origin remote already exists"
    fi
    
    # Show current remotes
    log_info "Current remotes:"
    git remote -v
}

# Install Python dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."
    
    if [[ -f "$PYTHON_REQUIREMENTS" ]]; then
        if command_exists pip3; then
            pip3 install -r "$PYTHON_REQUIREMENTS" --upgrade
            log_success "Python dependencies installed"
        else
            log_warning "pip3 not found, skipping Python dependencies"
        fi
    else
        log_warning "requirements.txt not found"
    fi
}

# Check git status and handle uncommitted changes
handle_git_status() {
    log_info "Checking git status..."
    
    # Check if there are any changes (tracked or untracked)
    local has_tracked_changes=false
    local has_untracked_files=false
    
    # Check for tracked file changes (modified, deleted, etc.)
    if ! git diff --quiet || ! git diff --cached --quiet; then
        has_tracked_changes=true
    fi
    
    # Check for untracked files
    if git ls-files --others --exclude-standard | grep -q .; then
        has_untracked_files=true
    fi
    
    # Process changes if any exist
    if [[ "$has_tracked_changes" == true ]] || [[ "$has_untracked_files" == true ]]; then
        log_warning "Uncommitted changes detected"
        git status --short
        
        # Add untracked files only if we also have tracked changes
        # This prevents committing only untracked files without any real changes
        if [[ "$has_untracked_files" == true ]] && [[ "$has_tracked_changes" != true ]]; then
            log_info "Only untracked files present - skipping auto-commit"
            log_info "Use 'git add' manually if you want to commit these files"
            return 0
        fi
        if [[ "$has_untracked_files" == true ]] && [[ "$has_tracked_changes" == true ]]; then
            log_info "Adding untracked files..."
            git add .
        fi
        
        # Commit changes if there are staged changes
        if ! git diff --cached --quiet; then
            log_info "Committing staged changes..."
            git commit -m "chore: maintenance script updates $(date '+%Y-%m-%d %H:%M:%S')"
            log_success "Changes committed"
        fi
    else
        log_success "Working directory is clean"
    fi
}

# Update branch with upstream changes
update_branch() {
    local current_branch
    current_branch=$(git branch --show-current)
    
    log_info "Current branch: $current_branch"
    
    # Fetch latest changes
    log_info "Fetching latest changes from origin..."
    git fetch origin
    
    # Check if branch has upstream tracking
    if git rev-parse --abbrev-ref --symbolic-full-name @{u} > /dev/null 2>&1; then
        local upstream_branch
        upstream_branch=$(git rev-parse --abbrev-ref --symbolic-full-name @{u})
        log_info "Upstream branch: $upstream_branch"
        
        # Check if we're behind upstream
        if git rev-list --count HEAD..@{u} > /dev/null 2>&1; then
            local behind_count
            behind_count=$(git rev-list --count HEAD..@{u})
            if [[ "$behind_count" -gt 0 ]]; then
                log_info "Branch is $behind_count commits behind upstream"
                log_info "Pulling latest changes..."
                git pull
                log_success "Branch updated with upstream changes"
            else
                log_success "Branch is up to date with upstream"
            fi
        fi
    else
        log_warning "No upstream branch set for $current_branch"
        log_info "Setting upstream to origin/$current_branch..."
        git branch --set-upstream-to="origin/$current_branch" "$current_branch"
        log_success "Upstream set to origin/$current_branch"
    fi
}

# Push changes to remote
push_changes() {
    local current_branch
    current_branch=$(git branch --show-current)
    
    log_info "Pushing changes to origin/$current_branch..."
    
    # Check if the remote branch exists
    if git ls-remote --exit-code --heads origin "$current_branch" >/dev/null 2>&1; then
        # Remote branch exists - check if we have commits to push
        local ahead_count
        ahead_count=$(git rev-list --count origin/$current_branch..HEAD 2>/dev/null || echo "0")
        
        if [[ "$ahead_count" -gt 0 ]]; then
            log_info "Branch is $ahead_count commits ahead of origin"
            git push origin "$current_branch"
            log_success "Changes pushed to origin"
        else
    # Check if the remote branch exists
    if git ls-remote --exit-code --heads origin "$current_branch" > /dev/null 2>&1; then
        fi
    else
        # Remote branch doesn't exist - first push, set upstream
        log_info "Remote branch doesn't exist - setting upstream..."
        git push -u origin "$current_branch"
        log_success "Initial push completed with upstream set"
    fi
}

# Main maintenance function
main() {
    log_info "Starting maintenance for $PROJECT_NAME..."
    
    # Check if we're in Codex environment
    if is_codex_environment; then
        log_info "Running in Codex environment"
    else
        log_info "Running in local environment"
    fi
    
    # Run maintenance steps
    check_git_repo
    setup_git_remotes
    install_dependencies
    handle_git_status
    update_branch
    push_changes
    
    log_success "Maintenance completed successfully!"
    
    # Show final status
    log_info "Final git status:"
    git status --short
    log_info "Current branch info:"
    git branch -vv
}

# Run main function
main "$@"
