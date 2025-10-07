#!/bin/bash
#
# Optimized Codex Setup Script for RunPod Serverless Environment
# This script sets up the Codex environment for the ComfyUI Serverless repo
# with improved error handling, validation, and Codex-specific optimizations
#
# Version: 3.0 (State-of-the-Art Optimized)
#

set -Eeuo pipefail
trap 'echo -e "${RED}❌ Error on line ${BASH_LINENO[0]}${NC}"' ERR

# Colors for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

echo_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Optional Logging
if [[ -n "${LOG_FILE:-}" ]]; then
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
    exec > >(tee -a "$LOG_FILE") 2>&1
    echo_info "📜 Logging to $LOG_FILE"
fi

RETRY_ATTEMPTS=${RETRY_ATTEMPTS:-3}
RETRY_DELAY=${RETRY_DELAY:-2}
PYTHON_CMD=python3

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_BASENAME="runpod-comfyui-serverless"
if [[ "$(basename "$SCRIPT_DIR")" == "$REPO_BASENAME" ]]; then
    PREEXISTING_REPO=true
else
    PREEXISTING_REPO=false
fi

# Function: Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Retry helper for flaky commands
retry() {
    local attempt=1
    local exit_code=0

    while true; do
        "$@" && return 0
        exit_code=$?

        if (( attempt >= RETRY_ATTEMPTS )); then
            return "$exit_code"
        fi

        echo_warning "Attempt ${attempt}/${RETRY_ATTEMPTS} failed – retrying in ${RETRY_DELAY}s"
        sleep "$RETRY_DELAY"
        attempt=$((attempt + 1))
    done
}

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
            retry sudo apt-get install -y "${missing[@]}" >/dev/null
        else
            echo_warning "apt-get update failed – skipping install for (${missing[*]})"
            return 1
        fi
    elif [ "$(id -u)" -eq 0 ]; then
        echo_info "Installing packages with root privileges: ${missing[*]}"
        if retry apt-get update -qq; then
            retry apt-get install -y "${missing[@]}" >/dev/null
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
    local packages=("runpod" "requests" "boto3" "PIL" "numpy")
    local all_ok=true
    
    echo_info "Validating Python packages..."
    
    for pkg in "${packages[@]}"; do
        # Special case for Pillow (imports as PIL)
        local import_name=$pkg
        [ "$pkg" = "PIL" ] && import_name="PIL"
        
        if $PYTHON_CMD -c "import $import_name" 2>/dev/null; then
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
if [ -d "/workspace" ] || [ -n "${CODEX_WORKSPACE:-}" ]; then
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
    if git clone https://github.com/EcomTree/runpod-comfyui-serverless.git "$REPO_DIR" >/tmp/git-clone.log 2>&1; then
        if grep -v "Cloning into" /tmp/git-clone.log 2>/dev/null; then
            :
        fi
        rm -f /tmp/git-clone.log
        cd "$REPO_DIR"
        echo_success "Repository cloned"
    else
        echo_error "Git clone failed"
        if [ -s /tmp/git-clone.log ]; then
            echo_warning "Details:" && cat /tmp/git-clone.log
        fi
        rm -f /tmp/git-clone.log
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

if git fetch origin main --tags >/tmp/git-fetch.log 2>&1; then
    if grep -v -E "^From|^remote:|^Fetching" /tmp/git-fetch.log 2>/dev/null; then
        :
    fi
    if git show-ref --verify --quiet refs/heads/main; then
        if ! git checkout main 2>/dev/null; then
            echo_warning "Local main branch broken – recreating from origin/main"
            git checkout -B main origin/main 2>&1 | grep -v "^Switched" || true
        fi
    else
        git checkout -B main origin/main 2>&1 | grep -v "^Switched" || true
    fi

    if git status --short --porcelain | grep -q ""; then
        echo_warning "Local changes present – skipping git pull"
        echo_info "Run 'git status' to see changes"
    else
        if git pull --ff-only origin main >/tmp/git-pull.log 2>&1; then
            if grep -v -E "^From|^Already" /tmp/git-pull.log 2>/dev/null; then
                :
            fi
            echo_success "Branch main successfully updated"
        else
            echo_warning "Could not update main – please check manually"
        fi
    fi
else
    echo_warning "Fetch from origin/main failed – working with existing copy"
fi
rm -f /tmp/git-fetch.log /tmp/git-pull.log

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
retry "$PYTHON_CMD" -m pip install --quiet --upgrade pip setuptools wheel 2>&1 | grep -v "^Requirement already satisfied" || true

echo_info "📦 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    echo_info "Using requirements.txt"
    retry "$PYTHON_CMD" -m pip install --quiet --no-cache-dir -r requirements.txt 2>&1 | \
        grep -v "^Requirement already satisfied\|^Using cached" || true
else
    echo_warning "requirements.txt not found - installing default packages"
    retry "$PYTHON_CMD" -m pip install --quiet --no-cache-dir \
        runpod \
        requests \
        boto3 \
        Pillow \
        numpy 2>&1 | \
        grep -v "^Requirement already satisfied\|^Using cached" || true
fi

validate_python_packages || {
    echo_warning "Package validation failed - some functionality may be limited"
}

# ============================================================
# 5. System Tools (optional - graceful degradation)
# ============================================================
echo_info "🔧 Ensuring system tools (optional)..."
ensure_system_packages jq curl git || echo_info "Some system tools could not be installed (non-critical)"

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
try:
    from rp_handler import handler
    print('✓ Handler importable')
except Exception as exc:
    raise SystemExit(str(exc))
PY
then
    echo_success "✓ rp_handler.py is valid"
else
    echo_warning "✗ rp_handler.py has issues (check logs)"
fi

# Check if all required files exist
REQUIRED_FILES=("rp_handler.py" "requirements.txt" "Serverless.Dockerfile" "README.md")
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
echo_success "✨ Setup completed successfully!"
echo ""
echo_info "📋 Environment Summary:"
echo "   ├─ Python: $($PYTHON_CMD --version 2>&1 | awk '{print $2}')"
echo "   ├─ pip: $($PYTHON_CMD -m pip --version 2>/dev/null | awk '{print $2}' || echo 'N/A')"
echo "   ├─ Node.js: $(node --version 2>/dev/null || echo 'not detected')"
echo "   ├─ jq: $(jq --version 2>/dev/null || echo 'not available')"
echo "   ├─ curl: $(curl --version 2>/dev/null | head -n1 | awk '{print $2}' || echo 'not available')"
echo "   └─ git: $(git --version 2>/dev/null | awk '{print $3}' || echo 'not available')"
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
echo "   4. For Docker build: docker build -f Serverless.Dockerfile ."
echo ""

# Codex-specific tips
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

