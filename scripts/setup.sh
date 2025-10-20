#!/bin/bash
#
# Unified Setup Script for RunPod ComfyUI Serverless Environment
# This script handles project setup, dependency installation, and environment configuration
#
# Version: 1.0 (Consolidated and Modular)
#

set -euo pipefail

# Script configuration
SCRIPT_VERSION="1.0"
PROJECT_NAME="runpod-comfyui-serverless"
DEFAULT_REPO_URL="https://github.com/EcomTree/runpod-comfyui-serverless.git"

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Logging functions
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

# Utility functions
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

retry() {
    local attempt=1
    local exit_code=0
    local max_attempts=${RETRY_ATTEMPTS:-3}
    local delay=${RETRY_DELAY:-2}

    while true; do
        "$@" && return 0
        exit_code=$?

        if (( attempt >= max_attempts )); then
            return "$exit_code"
        fi

        log_warning "Attempt ${attempt}/${max_attempts} failed – retrying in ${delay}s"
        sleep "$delay"
        attempt=$((attempt + 1))
    done
}

# Configuration
get_script_dir() {
    local source="${BASH_SOURCE[0]}"
    local dir

    if [[ -n "$source" ]]; then
        dir="$(dirname "$source")"
    else
        dir="$(dirname "$0")"
    fi

    if [[ -d "$dir" ]]; then
        (cd "$dir" && pwd)
    else
        pwd
    fi
}

SCRIPT_DIR="$(get_script_dir)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Detect environment
is_codex_environment() {
    [ -n "${CODEX_CONTAINER:-}" ] || \
    [ -n "${RUNPOD_POD_ID:-}" ] || \
    [ -n "${CODEX_WORKSPACE:-}" ] || \
    [ -d "/workspace" ]
}

# Python dependencies
PYTHON_PACKAGES=("runpod" "requests" "boto3" "Pillow" "numpy")
PYTHON_IMPORT_NAMES=("runpod" "requests" "boto3" "PIL" "numpy")

# Check Python version
check_python_version() {
    local required_major=3
    local required_minor=11

    if ! command_exists python3; then
        log_error "Python 3 is not installed"
        return 1
    fi

    local version=$(python3 --version 2>&1 | awk '{print $2}')
    local major=$(echo "$version" | cut -d. -f1)
    local minor=$(echo "$version" | cut -d. -f2)

    log_info "Python Version: $version"

    if ! [[ "$major" =~ ^[0-9]+$ ]] || ! [[ "$minor" =~ ^[0-9]+$ ]]; then
        log_warning "Could not parse version numbers from $version"
        return 0
    fi

    if [ "$major" -lt "$required_major" ] || ([ "$major" -eq "$required_major" ] && [ "$minor" -lt "$required_minor" ]); then
        log_warning "Python $required_major.$required_minor+ recommended, found $version"
        return 0
    fi

    log_success "Python version check passed"
    return 0
}

# Install system packages
install_system_packages() {
    local packages=("$@")
    local missing=()

    for pkg in "${packages[@]}"; do
        if command_exists "$pkg"; then
            log_success "$pkg available"
        else
            missing+=("$pkg")
        fi
    done

    if (( ${#missing[@]} == 0 )); then
        return 0
    fi

    if ! command_exists apt-get; then
        log_warning "apt-get not available – skipping install for (${missing[*]})"
        return 1
    fi

    if command_exists sudo && sudo -n true 2>/dev/null; then
        log_info "Installing packages via sudo apt-get: ${missing[*]}"
        if retry sudo apt-get update -qq; then
            retry sudo apt-get install -y "${missing[@]}"
        else
            log_warning "apt-get update failed – skipping install for (${missing[*]})"
            return 1
        fi
    elif [ "$(id -u)" -eq 0 ]; then
        log_info "Installing packages with root privileges: ${missing[*]}"
        if retry apt-get update -qq; then
            retry apt-get install -y "${missing[@]}"
        else
            log_warning "apt-get update failed – skipping install for (${missing[*]})"
            return 1
        fi
    else
        log_warning "No sudo privileges – cannot install packages (${missing[*]})"
        return 1
    fi

    for pkg in "${missing[@]}"; do
        if command_exists "$pkg"; then
            log_success "$pkg installed"
        else
            log_warning "$pkg installation failed"
        fi
    done
}

# Validate Python packages
validate_python_packages() {
    local all_ok=true

    log_info "Validating Python packages..."

    for pkg in "${PYTHON_IMPORT_NAMES[@]}"; do
        if python3 -c "import $pkg" 2>/dev/null; then
            log_success "✓ $pkg"
        else
            log_warning "✗ $pkg not found"
            all_ok=false
        fi
    done

    if $all_ok; then
        log_success "All Python packages validated"
        return 0
    else
        log_warning "Some packages missing - may cause issues"
        return 1
    fi
}

# Setup workspace
setup_workspace() {
    log_info "Setting up workspace..."

    if [ -d "/workspace" ]; then
        cd /workspace
        WORKSPACE_DIR="/workspace"
    else
        if mkdir -p /workspace; then
            cd /workspace
            WORKSPACE_DIR="/workspace"
        else
            log_error "Failed to create /workspace directory. Check permissions."
            exit 1
        fi
    fi

    log_success "Workspace ready: $(pwd)"
}

# Clone or update repository
setup_repository() {
    local repo_url="${1:-$DEFAULT_REPO_URL}"

    if [ -d "$PROJECT_ROOT" ]; then
        log_info "Project directory already exists, skipping clone"
        cd "$PROJECT_ROOT"
        return 0
    fi

    log_info "Cloning repository..."
    if retry git clone "$repo_url" "$PROJECT_ROOT"; then
        cd "$PROJECT_ROOT"
        log_success "Repository cloned"
    else
        log_error "Failed to clone repository"
        exit 1
    fi
}

# Setup Python environment
setup_python_environment() {
    log_info "Setting up Python environment..."

    if [ ! -d ".venv" ]; then
        log_info "Creating virtual environment"
        python3 -m venv .venv
    else
        log_info "Using existing virtual environment"
    fi

    source .venv/bin/activate
    PYTHON_CMD="$(command -v python)"

    log_info "Upgrading pip and core packages"
    retry "$PYTHON_CMD" -m pip install --quiet --upgrade pip setuptools wheel

    log_info "Installing Python dependencies"
    if [ -f "requirements.txt" ]; then
        retry "$PYTHON_CMD" -m pip install --quiet --no-cache-dir -r requirements.txt
    else
        retry "$PYTHON_CMD" -m pip install --quiet --no-cache-dir "${PYTHON_PACKAGES[@]}"
    fi

    validate_python_packages || log_warning "Package validation failed"
    log_success "Python environment ready"
}

# Setup configuration files
setup_configuration() {
    log_info "Setting up configuration files..."

    # Create .env.example if it doesn't exist
    if [ ! -f ".env.example" ]; then
        cat > .env.example << 'EOF'
# ComfyUI Configuration
COMFY_PORT=8188
COMFY_HOST=127.0.0.1
RANDOMIZE_SEEDS=true

# Storage Configuration - S3 (Recommended)
S3_BUCKET=
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_ENDPOINT_URL=
S3_REGION=auto
S3_PUBLIC_URL=
S3_SIGNED_URL_EXPIRY=3600
S3_CACHE_CONTROL=public, max-age=31536000

# Cleanup Configuration
CLEANUP_TEMP_FILES=true

# Container Caching
ENABLE_CONTAINER_CACHE=true

# Network Volume (Fallback)
RUNPOD_VOLUME_PATH=/runpod-volume
RUNPOD_OUTPUT_DIR=

# Model Refresh
COMFYUI_REFRESH_MODELS=true

# Logging
DEBUG_S3_URLS=false
EOF
        log_success ".env.example created"
    fi

    # Create .env if it doesn't exist
    if [ ! -f ".env" ]; then
        cp .env.example .env
        log_warning "Please edit .env and add your configuration!"
    fi

    # Create output directories
    mkdir -p outputs logs
    log_success "Configuration files and directories created"
}

# Setup git configuration
setup_git() {
    log_info "Setting up git configuration..."

    # Configure git user if not set
    if [ -z "$(git config --global user.email 2>/dev/null || true)" ]; then
        git config --global user.email "${GIT_USER_EMAIL:-codex@runpod.io}" 2>/dev/null && \
            log_success "Git email configured" || \
            log_warning "Could not set git email"
    fi

    if [ -z "$(git config --global user.name 2>/dev/null || true)" ]; then
        git config --global user.name "${GIT_USER_NAME:-Codex User}" 2>/dev/null && \
            log_success "Git name configured" || \
            log_warning "Could not set git name"
    fi

    git config --global init.defaultBranch main 2>/dev/null && \
        log_success "Git default branch configured" || \
        log_warning "Could not set git default branch"
}

# Test handler import
test_handler_import() {
    PYTHONPATH="$(pwd):$PYTHONPATH" python3 - <<'EOF'
import sys
sys.path.insert(0, '.')
try:
    from rp_handler import handler
    sys.exit(0)
except Exception as e:
    print(f"Import failed: {e}", file=sys.stderr)
    sys.exit(1)
EOF
}


# Validate setup
validate_setup() {
    log_info "Validating setup..."

    # Check Python syntax
    if [ -f "rp_handler.py" ]; then
        if python3 -m py_compile rp_handler.py 2>/dev/null; then
            log_success "✓ Python syntax valid"
        else
            log_warning "✗ Python syntax issues detected"
        fi
    else
        log_warning "✗ rp_handler.py not found in current directory"
    fi

    # Check if handler can be imported
    if [ -f "rp_handler.py" ]; then
        if test_handler_import 2>/dev/null; then
            log_success "✓ Handler importable"
        else
            log_warning "✗ Handler import issues"
        fi
    else
        log_warning "✗ Cannot test handler import - rp_handler.py not found"
    fi

    # Check required files
    local required_files=("rp_handler.py" "requirements.txt" "Dockerfile" "README.md")
    for file in "${required_files[@]}"; do
        if [ -f "$file" ]; then
            log_success "✓ $file"
        else
            log_warning "✗ $file missing"
        fi
    done

    log_success "Setup validation completed"
}

# Main setup function
main() {
    log_info "🚀 Starting $PROJECT_NAME setup v$SCRIPT_VERSION"

    # Check environment
    if is_codex_environment; then
        log_success "Codex environment detected"
        export IN_CODEX=true
    else
        log_warning "Not in Codex environment - some features may differ"
        export IN_CODEX=false
    fi

    # Run pre-flight checks
    log_info "🔍 Running pre-flight checks..."
    check_python_version || log_warning "Python version check failed"

    # Setup workspace
    setup_workspace

    # Setup repository
    setup_repository "$@"

    # Setup Python environment
    setup_python_environment

    # Setup configuration
    setup_configuration

    # Setup git
    setup_git

    # Validate setup
    validate_setup

    # Show summary
    echo
    log_success "✨ Setup completed successfully!"
    echo
    log_info "📋 Environment Summary:"
    echo "   ├─ Python: $(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -n1 || echo 'N/A')"
    echo "   ├─ pip: $(python3 -m pip --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -n1 || echo 'N/A')"
    echo "   ├─ Workspace: $(pwd)"
    echo "   ├─ Virtualenv: $(dirname "$(command -v python)")"
    echo
    log_info "📝 Next steps:"
    echo "   1. Edit .env and configure your settings (especially S3)"
    echo "   2. Test the handler: python3 -c 'from rp_handler import handler'"
    echo "   3. For Docker build: docker build -f Dockerfile ."
    echo

    if [ "$IN_CODEX" = true ]; then
        log_info "💡 Codex-specific tips:"
        echo "   • Enable 'Container Caching' for faster restarts"
        echo "   • Use S3 (Cloudflare R2/AWS S3) for persistent storage"
        echo "   • Set environment variables via Codex UI"
        echo "   • Reference: https://docs.runpod.io/serverless/endpoints/endpoint-configurations"
        echo
    fi

    log_success "🎉 Environment is ready!"
}

# Run main function with all arguments
main "$@"
