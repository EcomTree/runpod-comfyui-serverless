#!/bin/bash
#
# Optimized Codex Setup Script for RunPod Serverless Environment
# This script sets up the Codex environment for the ComfyUI Serverless repo
# with improved error handling, validation, and Codex-specific optimizations
#
# Version: 3.0 (State-of-the-Art Optimized)
#

set -Ee
set -o pipefail

DEFAULT_REPO_NAME="runpod-comfyui-serverless"

get_script_dir() {
    local source="${BASH_SOURCE[0]:-}"

    if [[ -z "$source" || "$source" == "bash" ]]; then
        source="${0:-}"
    fi

    if [[ -z "$source" || "$source" == "bash" ]]; then
        printf '%s\n' "$(pwd)"
        return
    fi

    local dir
    dir="$(dirname "$source" 2>/dev/null || printf '.\n')"

    # Use subshell to avoid changing the caller's working directory
    (cd "$dir" 2>/dev/null && pwd) || pwd
}

SCRIPT_DIR="$(get_script_dir)"

if [[ -z "${REPO_BASENAME:-}" ]]; then
    # SCRIPT_DIR is always set (at minimum to '.'), so we can use it directly
    REPO_BASENAME="$(basename "${SCRIPT_DIR}")"
    
    # Fallback if basename returns invalid values
    if [[ -z "${REPO_BASENAME}" || "${REPO_BASENAME}" == "." || "${REPO_BASENAME}" == "/" ]]; then
        REPO_BASENAME="${DEFAULT_REPO_NAME}"
    fi
fi

set -u
trap 'printf "❌ Error on line %s\n" "${BASH_LINENO[0]}" >&2' ERR

# Common helper script resolution order:
# 1. COMMON_HELPERS_PATH environment variable (if set, highest priority)
# 2. Local paths (SCRIPT_DIR and PWD relative)
# 3. Workspace paths (/workspace and /workspace/<REPO_BASENAME>)
# 4. CODEX_WORKSPACE environment variable paths (if set)
# The first readable file found will be sourced; if none found, inline fallback helpers are used.
COMMON_HELPERS=""
declare -a COMMON_HELPERS_CANDIDATES=(
    "${SCRIPT_DIR}/scripts/common-codex.sh"
    "${SCRIPT_DIR}/../scripts/common-codex.sh"
    "${PWD}/scripts/common-codex.sh"
    "${PWD}/../scripts/common-codex.sh"
    "/workspace/${REPO_BASENAME}/scripts/common-codex.sh"
    "/workspace/scripts/common-codex.sh"
)

if [[ -n "${CODEX_WORKSPACE:-}" ]]; then
    COMMON_HELPERS_CANDIDATES+=(
        "${CODEX_WORKSPACE}/scripts/common-codex.sh"
        "${CODEX_WORKSPACE}/${REPO_BASENAME}/scripts/common-codex.sh"
    )
fi

if [[ -n "${COMMON_HELPERS_PATH:-}" ]]; then
    COMMON_HELPERS_CANDIDATES=("${COMMON_HELPERS_PATH}" "${COMMON_HELPERS_CANDIDATES[@]}")
fi

for candidate in "${COMMON_HELPERS_CANDIDATES[@]}"; do
    if [[ -n "$candidate" && -f "$candidate" && -r "$candidate" ]]; then
        COMMON_HELPERS="$candidate"
        break
    fi
done

if [[ -n "$COMMON_HELPERS" && -f "$COMMON_HELPERS" && -r "$COMMON_HELPERS" ]]; then
    # shellcheck disable=SC1090
    source "$COMMON_HELPERS"
else
    # Fallback: inline minimal helpers for standalone execution
    echo "⚠️  Helper script not found, using inline fallback" >&2
    GREEN='\033[0;32m'
    BLUE='\033[0;34m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    NC='\033[0m'
    
    echo_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
    echo_success() { echo -e "${GREEN}✅ $1${NC}"; }
    echo_warning() { echo -e "${YELLOW}⚠️  $1${NC}" >&2; }
    echo_error() { echo -e "${RED}❌ $1${NC}" >&2; }
    command_exists() { command -v "$1" >/dev/null 2>&1; }
    
    retry() {
        local attempt=1 exit_code=0
        local max_attempts=${RETRY_ATTEMPTS:-3} delay=${RETRY_DELAY:-2}
        while true; do
            "$@" && return 0
            exit_code=$?
            if (( attempt >= max_attempts )); then return "$exit_code"; fi
            echo_warning "Attempt ${attempt}/${max_attempts} failed – retrying in ${delay}s"
            sleep "$delay"
            attempt=$((attempt + 1))
        done
    }
    
    is_codex_environment() {
        [ -n "${CODEX_CONTAINER:-}" ] || \
        [ -n "${RUNPOD_POD_ID:-}" ] || \
        [ -n "${CODEX_WORKSPACE:-}" ] || \
        [ -d "/workspace" ]
    }
fi

# Override trap with colored version now that color variables are available
trap 'echo -e "${RED}❌ Error on line ${BASH_LINENO[0]}${NC}" >&2' ERR

# Optional Logging
if [[ -n "${LOG_FILE:-}" ]]; then
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
    exec > >(tee -a "$LOG_FILE") 2>&1
    echo_info "📜 Logging to $LOG_FILE"
fi

RETRY_ATTEMPTS=${RETRY_ATTEMPTS:-3}
RETRY_DELAY=${RETRY_DELAY:-2}
PYTHON_CMD=python3

# Python packages to install and validate
PYTHON_PACKAGES=("runpod" "requests" "boto3" "Pillow" "numpy")
PYTHON_IMPORT_NAMES=("runpod" "requests" "boto3" "PIL" "numpy")

# Check if we're already in the target repository
# Compare against the expected repo name (hardcoded) to avoid self-match with dynamic REPO_BASENAME
EXPECTED_REPO_NAME="${EXPECTED_REPO_NAME:-$DEFAULT_REPO_NAME}"
if [[ "$(basename "$SCRIPT_DIR")" == "$EXPECTED_REPO_NAME" ]]; then
    PREEXISTING_REPO=true
else
    PREEXISTING_REPO=false
fi

# Function: Check Python version
check_python_version() {
    local required_major=3
    local required_minor=11

    if ! command_exists "$PYTHON_CMD"; then
        echo_error "Python 3 is not installed"
        return 1
    fi

    local version=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    local major=$(echo "$version" | cut -d. -f1)
    local minor=$(echo "$version" | cut -d. -f2)

    echo_info "Python Version: $version"

    # Validate that major and minor are numeric
    if ! [[ "$major" =~ ^[0-9]+$ ]] || ! [[ "$minor" =~ ^[0-9]+$ ]]; then
        echo_warning "Could not parse version numbers from $version"
        return 0
    fi

    if [ "$major" -lt "$required_major" ] || ([ "$major" -eq "$required_major" ] && [ "$minor" -lt "$required_minor" ]); then
        echo_warning "Python $required_major.$required_minor+ recommended, found $version"
        return 0
    fi

    echo_success "Python version check passed"
    return 0
}

# Function: Ensure system packages
ensure_system_packages() {
    local packages=("$@")
    local missing=()

    for pkg in "${packages[@]}"; do
        if command_exists "$pkg"; then
            echo_success "$pkg available"
        else
            missing+=("$pkg")
        fi
    done

    if (( ${#missing[@]} == 0 )); then
        return 0
    fi

    if ! command_exists apt-get; then
        echo_warning "apt-get not available – skipping install for (${missing[*]})"
        return 1
    fi

    if command_exists sudo && sudo -n true 2>/dev/null; then
        echo_info "Installing packages via sudo apt-get: ${missing[*]}"
        if retry sudo apt-get update -qq; then
            retry sudo apt-get install -y "${missing[@]}"
        else
            echo_warning "apt-get update failed – skipping install for (${missing[*]})"
            return 1
        fi
    elif [ "$(id -u)" -eq 0 ]; then
        echo_info "Installing packages with root privileges: ${missing[*]}"
        if retry apt-get update -qq; then
            retry apt-get install -y "${missing[@]}"
        else
            echo_warning "apt-get update failed – skipping install for (${missing[*]})"
            return 1
        fi
    else
        echo_warning "No sudo privileges – cannot install packages (${missing[*]})"
        return 1
    fi

    for pkg in "${missing[@]}"; do
        if command_exists "$pkg"; then
            echo_success "$pkg installed"
        else
            echo_warning "$pkg installation failed"
        fi
    done
}

# Function to validate Python package installation
validate_python_packages() {
    local all_ok=true
    
    echo_info "Validating Python packages..."
    
    for pkg in "${PYTHON_IMPORT_NAMES[@]}"; do
        if $PYTHON_CMD -c "import $pkg" 2>/dev/null; then
            echo_success "✓ $pkg"
        else
            echo_warning "✗ $pkg not found"
            all_ok=false
        fi
    done
    
    if $all_ok; then
        echo_success "All Python packages validated"
        return 0
    else
        echo_warning "Some packages missing - may cause issues"
        return 1
    fi
}

echo_info "🚀 Starting Codex environment setup for RunPod ComfyUI Serverless..."
echo_info "📝 Script Version: 3.0 (State-of-the-Art Optimized)"

# ============================================================
# 0. Pre-flight Checks
# ============================================================
echo_info "🔍 Running pre-flight checks..."

# Check if we're in Codex environment (typical indicators)
if is_codex_environment; then
    echo_success "Codex environment detected"
    export IN_CODEX=true
else
    echo_warning "Not in typical Codex environment - some features may differ"
    export IN_CODEX=false
fi

# Check Python version
check_python_version || {
    echo_warning "Python version check failed - continuing anyway"
}

# ============================================================
# 1. Create Workspace Directory
# ============================================================
echo_info "📁 Creating workspace structure..."
if $PREEXISTING_REPO; then
    WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"
    cd "$WORKSPACE_DIR"
    echo_success "Workspace ready (existing repo): $(pwd)"
else
    if mkdir -p /workspace 2>/dev/null; then
        cd /workspace
        WORKSPACE_DIR="/workspace"
    else
        echo_warning "Could not create /workspace - using current directory"
        WORKSPACE_DIR="$(pwd)"
    fi
    echo_success "Workspace ready: $(pwd)"
fi

# ============================================================
# 2. Clone Repository (if not present)
# ============================================================
if $PREEXISTING_REPO; then
    REPO_DIR="$SCRIPT_DIR"
else
    REPO_DIR="${WORKSPACE_DIR}/${REPO_BASENAME}"
fi

if $PREEXISTING_REPO; then
    echo_info "📦 Existing repository detected at $REPO_DIR"
    cd "$REPO_DIR"
elif [ ! -d "$REPO_DIR" ]; then
    echo_info "📦 Cloning repository..."
    GIT_CLONE_LOG="$(mktemp /tmp/git-clone.XXXXXX.log)"
    if retry bash -c "git clone https://github.com/EcomTree/runpod-comfyui-serverless.git '$REPO_DIR' >'$GIT_CLONE_LOG' 2>&1"; then
        rm -f "$GIT_CLONE_LOG"
        cd "$REPO_DIR"
        echo_success "Repository cloned"
    else
        echo_error "Git clone failed"
        if [ -s "$GIT_CLONE_LOG" ]; then
            echo_warning "Details:" && cat "$GIT_CLONE_LOG"
        fi
        rm -f "$GIT_CLONE_LOG"
        exit 1
    fi
elif [ -d "$REPO_DIR" ]; then
    echo_warning "Repository already exists, skipping clone"
    cd "$REPO_DIR"
fi

# ============================================================
# 3. Git Branch Management
# ============================================================
echo_info "🌿 Ensuring repository is on main branch..."

GIT_FETCH_LOG="$(mktemp /tmp/git-fetch.XXXXXX.log)"
GIT_PULL_LOG="$(mktemp /tmp/git-pull.XXXXXX.log)"

# EXPECTED_REPO_BRANCH: Environment variable to specify the target branch to checkout
# Defaults to 'main' if not set. Use this to work with feature branches or other default branches.
TARGET_BRANCH="${EXPECTED_REPO_BRANCH:-main}"

if retry bash -c "git fetch origin ${TARGET_BRANCH} --tags >'$GIT_FETCH_LOG' 2>&1"; then
    if git rev-parse --verify HEAD >/dev/null 2>&1; then
        CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
        echo_info "📦 Repository currently on branch: ${CURRENT_BRANCH}"
        
        # Check if we need to switch to the target branch
        if [[ "${CURRENT_BRANCH}" != "${TARGET_BRANCH}" ]]; then
            echo_info "Switching from ${CURRENT_BRANCH} to ${TARGET_BRANCH}..."
            if git show-ref --verify --quiet "refs/heads/${TARGET_BRANCH}"; then
                if ! git checkout "${TARGET_BRANCH}" 2>/dev/null; then
                    echo_warning "Local ${TARGET_BRANCH} branch broken – recreating from origin/${TARGET_BRANCH}"
                    git checkout -B "${TARGET_BRANCH}" "origin/${TARGET_BRANCH}" 2>&1 | grep -v "^Switched" || true
                fi
            else
                git checkout -B "${TARGET_BRANCH}" "origin/${TARGET_BRANCH}" 2>&1 | grep -v "^Switched" || true
            fi
        else
            echo_success "Already on ${TARGET_BRANCH} branch"
        fi
    else
        # No valid HEAD - create/checkout the target branch
        if git show-ref --verify --quiet "refs/heads/${TARGET_BRANCH}"; then
            git checkout "${TARGET_BRANCH}" 2>&1 | grep -v "^Switched" || true
        else
            git checkout -B "${TARGET_BRANCH}" "origin/${TARGET_BRANCH}" 2>&1 | grep -v "^Switched" || true
        fi
    fi

    if git status --short --porcelain | grep -q ""; then
        echo_warning "Local changes present – skipping git pull"
        echo_info "Run 'git status' to see changes"
    else
        if retry bash -c "git pull --ff-only origin ${TARGET_BRANCH} >'$GIT_PULL_LOG' 2>&1"; then
            echo_success "Branch ${TARGET_BRANCH} successfully updated"
        else
            echo_warning "Could not update ${TARGET_BRANCH} – please check manually"
        fi
    fi
else
    echo_warning "Fetch from origin/${TARGET_BRANCH} failed – working with existing copy"
fi
rm -f "$GIT_FETCH_LOG" "$GIT_PULL_LOG"

# ============================================================
# 4. Python Environment Setup (with venv)
# ============================================================
echo_info "🐍 Setting up Python environment..."

if [ -f ".venv/bin/activate" ]; then
    echo_info "Reusing existing virtual environment"
else
    echo_info "Creating virtual environment (.venv)"
    retry "$PYTHON_CMD" -m venv .venv
fi

source .venv/bin/activate
PYTHON_CMD="$(command -v python)"

echo_success "Virtual environment active: $PYTHON_CMD"

echo_info "Upgrading pip, setuptools, wheel..."
retry "$PYTHON_CMD" -m pip install --quiet --upgrade pip setuptools wheel 2>&1 \
    | grep -v "^Requirement already satisfied" || true

echo_info "📦 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    echo_info "Using requirements.txt"
    retry "$PYTHON_CMD" -m pip install --quiet --no-cache-dir -r requirements.txt 2>&1 \
        | grep -v "^Requirement already satisfied\|^Using cached" || true
else
    echo_warning "requirements.txt not found - installing default packages"
    retry "$PYTHON_CMD" -m pip install --quiet --no-cache-dir \
        "${PYTHON_PACKAGES[@]}" 2>&1 \
        | grep -v "^Requirement already satisfied\|^Using cached" || true
fi

validate_python_packages || {
    echo_warning "Package validation failed - some functionality may be limited"
}

# ============================================================
# 5. System Tools (optional - graceful degradation)
# ============================================================
echo_info "🔧 Ensuring system tools (optional)..."
ensure_system_packages jq curl git || echo_info "Some system tools could not be installed (non-critical)"
if ! command_exists jq; then
    echo_warning "jq missing - consider installing manually for JSON-friendly logs"
fi

# ============================================================
# 6. Environment Variables Setup
# ============================================================
echo_info "🌍 Configuring environment variables..."

# Create .env.example template if not present
if [ ! -f ".env.example" ]; then
    cat > .env.example << 'EOF'
# ComfyUI Configuration
COMFY_PORT=8188
COMFY_HOST=127.0.0.1
RANDOMIZE_SEEDS=true

# Storage Configuration - S3 (Recommended for Codex)
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

# Container Caching (Codex)
ENABLE_CONTAINER_CACHE=true

# Network Volume (Fallback - not available in Codex)
RUNPOD_VOLUME_PATH=/runpod-volume
RUNPOD_OUTPUT_DIR=

# Model Refresh
COMFYUI_REFRESH_MODELS=true

# Logging
DEBUG_S3_URLS=false
EOF
    echo_success ".env.example created"
else
    echo_success ".env.example already exists"
fi

# Create .env from .env.example if it doesn't exist
if [ ! -f ".env" ]; then
    echo_info "Creating .env from .env.example"
    cp .env.example .env
    echo_warning "⚠️  Please edit .env and add your configuration!"
fi

# ============================================================
# 7. Output Directory Structure
# ============================================================
echo_info "📂 Creating output directories..."

mkdir -p "${WORKSPACE_DIR}/outputs" 2>/dev/null || echo_warning "Could not create /workspace/outputs"
mkdir -p "${WORKSPACE_DIR}/logs" 2>/dev/null || echo_warning "Could not create /workspace/logs"

# Network Volume - expected to NOT exist in Codex
if [ "$IN_CODEX" = true ]; then
    echo_info "📦 Codex detected: Network Volume (/runpod-volume) not expected"
    echo_info "💡 Use S3 storage for persistent file storage"
else
    mkdir -p /runpod-volume 2>/dev/null || echo_info "Network Volume not available (expected in Codex)"
fi

echo_success "Directory structure created"

# ============================================================
# 8. Prepare Test Scripts
# ============================================================
echo_info "🧪 Preparing test environment..."

# Make test_endpoint.sh executable if it exists
if [ -f "test_endpoint.sh" ]; then
    chmod +x test_endpoint.sh 2>/dev/null || echo_warning "Could not make test_endpoint.sh executable"
    echo_success "Test script made executable"
else
    echo_info "test_endpoint.sh not found (optional)"
fi

# ============================================================
# 9. Git Configuration (safe approach)
# ============================================================
echo_info "🔧 Configuring Git..."

# Only set git config if not already set and if we have write access to git config
if [ -z "$(git config --global user.email 2>/dev/null || true)" ]; then
    if git config --global user.email "${GIT_USER_EMAIL:-codex@runpod.io}" 2>/dev/null; then
        echo_success "Git email configured"
    else
        echo_warning "Could not set git email (non-critical)"
    fi
fi

if [ -z "$(git config --global user.name 2>/dev/null || true)" ]; then
    if git config --global user.name "${GIT_USER_NAME:-Codex User}" 2>/dev/null; then
        echo_success "Git name configured"
    else
        echo_warning "Could not set git name (non-critical)"
    fi
fi

if git config --global init.defaultBranch main 2>/dev/null; then
    echo_success "Git default branch configured"
else
    echo_warning "Could not set git default branch (non-critical)"
fi

# ============================================================
# 10. Validation & Health Check
# ============================================================
echo ""
echo_info "🏥 Running health checks..."

echo_info "🔎 Static analysis"
if $PYTHON_CMD -m py_compile rp_handler.py 2>/dev/null; then
    echo_success "✓ Python syntax valid"
else
    echo_warning "✗ Python syntax issues detected"
fi

if $PYTHON_CMD - <<'PY'
import traceback
try:
    from rp_handler import handler
    print('✓ Handler importable')
except ImportError as e:
    print(f"ImportError: {e}")
    traceback.print_exc()
    raise SystemExit(1)
except SyntaxError as e:
    print(f"SyntaxError: {e}")
    traceback.print_exc()
    raise SystemExit(1)
except Exception as e:
    print(f"Unexpected exception ({type(e).__name__}): {e}")
    traceback.print_exc()
    raise SystemExit(1)
PY
then
    echo_success "✓ rp_handler.py is valid"
else
    echo_warning "✗ rp_handler.py has issues (check logs)"
fi

# Check if all required files exist
REQUIRED_FILES=("rp_handler.py" "requirements.txt" "Dockerfile" "README.md")
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo_success "✓ $file"
    else
        echo_warning "✗ $file missing"
    fi
done

# ============================================================
# 11. Final Summary
# ============================================================
echo ""
PYTHON_VERSION="$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -n1 || echo 'N/A')"
PIP_VERSION="$($PYTHON_CMD -m pip --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -n1 || echo 'N/A')"
DOCKER_VERSION="$(docker --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -n1 || echo 'not available')"
NODE_VERSION="$(node --version 2>/dev/null || echo 'not available')"
JQ_VERSION="$(jq --version 2>/dev/null || echo 'not available')"
CURL_VERSION="$(curl --version 2>/dev/null | head -n1 | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -n1 || echo 'not available')"
GIT_VERSION="$(git --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -n1 || echo 'not available')"

echo ""
echo_success "✨ Setup completed successfully!"
echo ""
echo_info "📋 Environment Summary:"
echo "   ├─ Python: $PYTHON_VERSION"
echo "   ├─ pip: $PIP_VERSION"
echo "   ├─ Docker: $DOCKER_VERSION"
echo "   ├─ Node.js: $NODE_VERSION"
echo "   ├─ jq: $JQ_VERSION"
echo "   ├─ curl: $CURL_VERSION"
echo "   └─ git: $GIT_VERSION"
echo ""
echo_info "📁 Paths:"
echo "   ├─ Workspace: $(pwd)"
echo "   ├─ Logs: ${WORKSPACE_DIR}/logs"
echo "   ├─ Outputs: ${WORKSPACE_DIR}/outputs"
echo "   ├─ Repo: $REPO_DIR"
echo "   └─ Virtualenv: $(dirname "$PYTHON_CMD")"
echo ""
echo_info "📝 Next steps:"
echo "   1. Edit .env and configure your settings (especially S3 for Codex)"
echo "   2. Test the handler: $PYTHON_CMD -c 'from rp_handler import handler'"
echo "   3. For local testing: $PYTHON_CMD rp_handler.py"
echo "   4. For Docker build: docker build -f Dockerfile ."
echo ""

if [ "$IN_CODEX" = true ]; then
    echo_info "💡 Codex-specific tips:"
    echo "   • Enable 'Container Caching' for faster restarts"
    echo "   • Use S3 (Cloudflare R2/AWS S3) for persistent storage"
    echo "   • Set environment variables via Codex UI"
    echo "   • Reference: https://docs.runpod.io/serverless/endpoints/endpoint-configurations"
    echo ""
fi

echo_success "🎉 Codex Environment is ready!"
echo ""

