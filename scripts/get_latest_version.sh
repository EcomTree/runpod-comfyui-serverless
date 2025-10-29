#!/bin/bash
#
# ComfyUI Version Management Script
# Fetches the latest ComfyUI version or validates a specific version
#

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

COMFYUI_REPO="comfyanonymous/ComfyUI"
GITHUB_API="https://api.github.com/repos/${COMFYUI_REPO}"

# Function to print colored messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to get latest release version
get_latest_release() {
    log_info "Fetching latest ComfyUI release from GitHub..."
    
    LATEST_VERSION=$(curl -s "${GITHUB_API}/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
    
    if [ -z "$LATEST_VERSION" ]; then
        log_error "Failed to fetch latest version"
        return 1
    fi
    
    log_info "Latest ComfyUI version: ${LATEST_VERSION}"
    echo "$LATEST_VERSION"
}

# Function to get all releases
get_all_releases() {
    log_info "Fetching all ComfyUI releases..."
    
    curl -s "${GITHUB_API}/releases" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/' | head -10
}

# Function to validate a specific version exists
validate_version() {
    local version=$1
    log_info "Validating version: ${version}"
    
    # Check if the tag exists
    STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${GITHUB_API}/git/refs/tags/${version}")
    
    if [ "$STATUS_CODE" = "200" ]; then
        log_info "Version ${version} is valid ✓"
        return 0
    else
        log_error "Version ${version} does not exist"
        return 1
    fi
}

# Function to get version from running ComfyUI
get_installed_version() {
    local comfyui_path="${1:-/workspace/ComfyUI}"
    
    if [ ! -d "$comfyui_path" ]; then
        log_warn "ComfyUI directory not found at ${comfyui_path}"
        return 1
    fi
    
    cd "$comfyui_path"
    
    if [ ! -d ".git" ]; then
        log_warn "Not a git repository"
        return 1
    fi
    
    # Get current git tag or commit
    CURRENT_TAG=$(git describe --tags --exact-match 2>/dev/null || echo "")
    
    if [ -n "$CURRENT_TAG" ]; then
        log_info "Currently installed version: ${CURRENT_TAG}"
        echo "$CURRENT_TAG"
    else
        CURRENT_COMMIT=$(git rev-parse --short HEAD)
        log_info "Currently on commit: ${CURRENT_COMMIT} (not a tagged release)"
        echo "commit-${CURRENT_COMMIT}"
    fi
}

# Function to compare versions
compare_versions() {
    local current_version=$1
    local latest_version=$2
    
    if [ "$current_version" = "$latest_version" ]; then
        log_info "You are running the latest version ✓"
        return 0
    else
        log_warn "Newer version available: ${latest_version} (current: ${current_version})"
        return 1
    fi
}

# Main script logic
main() {
    local command=${1:-"latest"}
    
    case $command in
        latest)
            get_latest_release
            ;;
        list)
            get_all_releases
            ;;
        validate)
            if [ -z "$2" ]; then
                log_error "Usage: $0 validate <version>"
                exit 1
            fi
            validate_version "$2"
            ;;
        installed)
            get_installed_version "$2"
            ;;
        check)
            INSTALLED=$(get_installed_version "$2")
            LATEST=$(get_latest_release)
            
            if [ -n "$INSTALLED" ] && [ -n "$LATEST" ]; then
                compare_versions "$INSTALLED" "$LATEST"
            fi
            ;;
        help|--help|-h)
            echo "ComfyUI Version Management"
            echo ""
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  latest              Get the latest release version"
            echo "  list                List recent releases"
            echo "  validate <version>  Check if a version exists"
            echo "  installed [path]    Get currently installed version"
            echo "  check [path]        Compare installed vs latest version"
            echo "  help                Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 latest"
            echo "  $0 validate v0.3.57"
            echo "  $0 installed /workspace/ComfyUI"
            echo "  $0 check"
            ;;
        *)
            log_error "Unknown command: $command"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

main "$@"
