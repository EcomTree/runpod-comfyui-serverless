#!/bin/bash
#
# ComfyUI Custom Nodes Installation Script
# Installs essential custom nodes based on configuration
#

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMFYUI_PATH="${COMFYUI_PATH:-/workspace/ComfyUI}"
CUSTOM_NODES_DIR="${COMFYUI_PATH}/custom_nodes"
CONFIG_FILE="${CONFIG_FILE:-/workspace/configs/custom_nodes.json}"
LOG_FILE="/workspace/logs/custom_nodes_install.log"

# Create logs directory
mkdir -p "$(dirname "$LOG_FILE")"

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1" | tee -a "$LOG_FILE"
}

# Check prerequisites
check_prerequisites() {
    log_step "Checking prerequisites..."
    
    if [ ! -d "$COMFYUI_PATH" ]; then
        log_error "ComfyUI not found at ${COMFYUI_PATH}"
        exit 1
    fi
    
    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "Configuration file not found at ${CONFIG_FILE}"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_warn "jq not installed, installing..."
        apt-get update && apt-get install -y jq
    fi
    
    if ! command -v git &> /dev/null; then
        log_error "git is not installed"
        exit 1
    fi
    
    log_info "Prerequisites check passed ✓"
}

# Parse JSON configuration
parse_config() {
    if ! jq empty "$CONFIG_FILE" 2>/dev/null; then
        log_error "Invalid JSON in configuration file"
        exit 1
    fi
    
    NODES_COUNT=$(jq '.custom_nodes | length' "$CONFIG_FILE")
    log_info "Found ${NODES_COUNT} custom nodes in configuration"
}

# Install a single custom node
install_node() {
    local name=$1
    local repo=$2
    local install_req=$3
    local priority=$4
    
    log_step "Installing node [${priority}]: ${name}"
    
    local node_dir="${CUSTOM_NODES_DIR}/${name}"
    
    # Check if already installed
    if [ -d "$node_dir" ]; then
        log_warn "Node ${name} already exists, updating..."
        cd "$node_dir"
        if [ -d ".git" ]; then
            git pull || log_warn "Failed to update ${name}"
        else
            log_warn "${node_dir} exists but is not a git repository, skipping"
            return 1
        fi
    else
        log_info "Cloning ${name} from ${repo}..."
        cd "$CUSTOM_NODES_DIR"
        if ! git clone "$repo" "$name"; then
            log_error "Failed to clone ${name}"
            return 1
        fi
        cd "$node_dir"
    fi
    
    # Install requirements if needed
    if [ "$install_req" = "true" ] && [ -f "requirements.txt" ]; then
        log_info "Installing requirements for ${name}..."
        if pip install --no-cache-dir -r requirements.txt; then
            log_info "Requirements installed successfully ✓"
        else
            log_warn "Failed to install some requirements for ${name}"
        fi
    fi
    
    # Run install script if exists
    if [ -f "install.py" ]; then
        log_info "Running install.py for ${name}..."
        python install.py || log_warn "install.py failed for ${name}"
    fi
    
    if [ -f "install.sh" ]; then
        log_info "Running install.sh for ${name}..."
        chmod +x install.sh
        ./install.sh || log_warn "install.sh failed for ${name}"
    fi
    
    log_info "Node ${name} installed successfully ✓"
    return 0
}

# Install all nodes from configuration
install_all_nodes() {
    log_step "Installing custom nodes..."
    
    mkdir -p "$CUSTOM_NODES_DIR"
    
    local success_count=0
    local failed_count=0
    
    # Get nodes sorted by priority
    local nodes=$(jq -r '.custom_nodes | sort_by(.priority) | .[] | @json' "$CONFIG_FILE")
    
    while IFS= read -r node; do
        name=$(echo "$node" | jq -r '.name')
        repo=$(echo "$node" | jq -r '.repo')
        install_req=$(echo "$node" | jq -r '.install_requirements')
        priority=$(echo "$node" | jq -r '.priority')
        required=$(echo "$node" | jq -r '.required')
        
        if install_node "$name" "$repo" "$install_req" "$priority"; then
            ((success_count++))
        else
            ((failed_count++))
            if [ "$required" = "true" ]; then
                log_error "Required node ${name} failed to install"
                if [ "${SKIP_ON_ERROR:-false}" != "true" ]; then
                    exit 1
                fi
            fi
        fi
        
        echo "" >> "$LOG_FILE"
    done <<< "$nodes"
    
    log_info "Installation complete: ${success_count} successful, ${failed_count} failed"
}

# Verify installations
verify_installations() {
    log_step "Verifying installations..."
    
    local nodes=$(jq -r '.custom_nodes[].name' "$CONFIG_FILE")
    local verified=0
    local failed=0
    
    while IFS= read -r name; do
        local node_dir="${CUSTOM_NODES_DIR}/${name}"
        if [ -d "$node_dir" ]; then
            log_info "✓ ${name}"
            ((verified++))
        else
            log_error "✗ ${name}"
            ((failed++))
        fi
    done <<< "$nodes"
    
    log_info "Verification: ${verified} verified, ${failed} missing"
}

# List installed nodes
list_nodes() {
    log_step "Listing installed custom nodes..."
    
    if [ ! -d "$CUSTOM_NODES_DIR" ]; then
        log_warn "Custom nodes directory does not exist"
        return
    fi
    
    local count=0
    for dir in "$CUSTOM_NODES_DIR"/*; do
        if [ -d "$dir" ]; then
            local name=$(basename "$dir")
            local has_init="❌"
            if [ -f "$dir/__init__.py" ] || [ -f "$dir/nodes.py" ]; then
                has_init="✓"
            fi
            echo "  ${has_init} ${name}"
            ((count++))
        fi
    done
    
    log_info "Total custom nodes: ${count}"
}

# Update all nodes
update_all_nodes() {
    log_step "Updating all custom nodes..."
    
    if [ ! -d "$CUSTOM_NODES_DIR" ]; then
        log_warn "No custom nodes directory found"
        return
    fi
    
    local updated=0
    local failed=0
    
    for dir in "$CUSTOM_NODES_DIR"/*; do
        if [ -d "$dir/.git" ]; then
            local name=$(basename "$dir")
            log_info "Updating ${name}..."
            
            cd "$dir"
            if git pull; then
                ((updated++))
                
                # Update requirements if changed
                if [ -f "requirements.txt" ]; then
                    pip install --no-cache-dir -r requirements.txt || log_warn "Failed to update requirements for ${name}"
                fi
            else
                log_warn "Failed to update ${name}"
                ((failed++))
            fi
        fi
    done
    
    log_info "Updates complete: ${updated} updated, ${failed} failed"
}

# Remove a node
remove_node() {
    local name=$1
    local node_dir="${CUSTOM_NODES_DIR}/${name}"
    
    if [ ! -d "$node_dir" ]; then
        log_error "Node ${name} not found"
        return 1
    fi
    
    log_warn "Removing node: ${name}"
    rm -rf "$node_dir"
    log_info "Node ${name} removed ✓"
}

# Main script
main() {
    local command=${1:-install}
    
    echo "========================================" | tee -a "$LOG_FILE"
    echo "ComfyUI Custom Nodes Installer" | tee -a "$LOG_FILE"
    echo "Date: $(date)" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    
    case $command in
        install)
            check_prerequisites
            parse_config
            install_all_nodes
            verify_installations
            ;;
        update)
            update_all_nodes
            ;;
        list)
            list_nodes
            ;;
        verify)
            check_prerequisites
            parse_config
            verify_installations
            ;;
        remove)
            if [ -z "$2" ]; then
                log_error "Usage: $0 remove <node_name>"
                exit 1
            fi
            remove_node "$2"
            ;;
        help|--help|-h)
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  install    Install all custom nodes from config (default)"
            echo "  update     Update all installed custom nodes"
            echo "  list       List all installed custom nodes"
            echo "  verify     Verify installations against config"
            echo "  remove     Remove a specific node"
            echo "  help       Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  COMFYUI_PATH       Path to ComfyUI installation (default: /workspace/ComfyUI)"
            echo "  CONFIG_FILE        Path to custom nodes config (default: /workspace/configs/custom_nodes.json)"
            echo "  SKIP_ON_ERROR      Continue on errors (default: false)"
            echo ""
            echo "Examples:"
            echo "  $0 install"
            echo "  $0 update"
            echo "  $0 list"
            echo "  $0 remove ComfyUI-Manager"
            ;;
        *)
            log_error "Unknown command: $command"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
    
    echo "" | tee -a "$LOG_FILE"
    log_info "Script completed at $(date)"
}

main "$@"
