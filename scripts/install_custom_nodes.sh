#!/bin/bash

# Install custom nodes for ComfyUI
# Usage: ./install_custom_nodes.sh [--config CONFIG_FILE] [--comfyui-path PATH]

set -e

# Default values
CONFIG_FILE="/workspace/configs/custom_nodes.json"
COMFYUI_PATH="/workspace/ComfyUI"
CUSTOM_NODES_PATH="/workspace/ComfyUI/custom_nodes"
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --comfyui-path)
            COMFYUI_PATH="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--config CONFIG_FILE] [--comfyui-path PATH] [--verbose]"
            echo "  --config CONFIG_FILE    Path to custom nodes config (default: /workspace/configs/custom_nodes.json)"
            echo "  --comfyui-path PATH     Path to ComfyUI installation (default: /workspace/ComfyUI)"
            echo "  --verbose               Enable verbose output"
            echo "  --help                  Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Verbose logging
vlog() {
    if [ "$VERBOSE" = true ]; then
        echo "[VERBOSE] $1"
    fi
}

# Check dependencies
check_dependencies() {
    log "Checking dependencies..."
    
    local missing_deps=()
    
    if ! command -v git &> /dev/null; then
        missing_deps+=("git")
    fi
    
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi
    
    if ! command -v pip3 &> /dev/null; then
        missing_deps+=("pip3")
    fi
    
    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log "❌ Missing dependencies: ${missing_deps[*]}"
        exit 1
    fi
    
    log "✅ All dependencies available"
}

# Check if config file exists
check_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        log "❌ Config file not found: $CONFIG_FILE"
        exit 1
    fi
    
    if ! jq empty "$CONFIG_FILE" 2>/dev/null; then
        log "❌ Invalid JSON in config file: $CONFIG_FILE"
        exit 1
    fi
    
    log "✅ Config file validated: $CONFIG_FILE"
}

# Install a single custom node
install_custom_node() {
    local name="$1"
    local repo="$2"
    local branch="$3"
    local requirements="$4"
    local priority="$5"
    
    log "Installing $name (priority: $priority)..."
    
    local node_path="$CUSTOM_NODES_PATH/$name"
    
    # Check if already installed
    if [ -d "$node_path" ]; then
        log "⚠️ $name already installed, updating..."
        cd "$node_path"
        git fetch origin
        git reset --hard "origin/$branch"
        git clean -fd
    else
        log "📥 Cloning $name from $repo..."
        cd "$CUSTOM_NODES_PATH"
        git clone -b "$branch" "$repo" "$name"
    fi
    
    # Install requirements if any
    if [ -n "$requirements" ] && [ "$requirements" != "null" ]; then
        log "📦 Installing requirements for $name..."
        cd "$node_path"
        
        # Check if requirements.txt exists
        if [ -f "requirements.txt" ]; then
            vlog "Installing from requirements.txt..."
            pip3 install --no-cache-dir -r requirements.txt
        fi
        
        # Install additional requirements from config
        if [ "$requirements" != "[]" ]; then
            vlog "Installing additional requirements: $requirements"
            echo "$requirements" | jq -r '.[]' | xargs -I {} pip3 install --no-cache-dir {}
        fi
    fi
    
    log "✅ $name installed successfully"
}

# Install all custom nodes
install_all_nodes() {
    log "Starting custom nodes installation..."
    
    # Create custom nodes directory
    mkdir -p "$CUSTOM_NODES_PATH"
    
    # Get installation order from config
    local install_order
    install_order=$(jq -r '.installation_order[]' "$CONFIG_FILE")
    
    # Install nodes in order
    while IFS= read -r node_name; do
        if [ -n "$node_name" ] && [ "$node_name" != "null" ]; then
            # Get node details
            local node_data
            node_data=$(jq -r --arg name "$node_name" '.custom_nodes[] | select(.name == $name)' "$CONFIG_FILE")
            
            if [ "$node_data" != "null" ] && [ -n "$node_data" ]; then
                local repo branch requirements priority
                repo=$(echo "$node_data" | jq -r '.repository')
                branch=$(echo "$node_data" | jq -r '.branch')
                requirements=$(echo "$node_data" | jq -r '.requirements')
                priority=$(echo "$node_data" | jq -r '.priority')
                
                install_custom_node "$node_name" "$repo" "$branch" "$requirements" "$priority"
            else
                log "⚠️ Node $node_name not found in config, skipping..."
            fi
        fi
    done <<< "$install_order"
}

# Run post-install commands
run_post_install() {
    log "Running post-install commands..."
    
    local post_commands
    post_commands=$(jq -r '.post_install_commands[]?' "$CONFIG_FILE")
    
    if [ -n "$post_commands" ] && [ "$post_commands" != "null" ]; then
        while IFS= read -r command; do
            if [ -n "$command" ] && [ "$command" != "null" ]; then
                log "Running: $command"
                eval "$command" || log "⚠️ Post-install command failed: $command"
            fi
        done <<< "$post_commands"
    fi
}

# Verify installation
verify_installation() {
    log "Verifying installation..."
    
    local installed_count=0
    local total_count=0
    
    # Count total nodes in config
    total_count=$(jq '.custom_nodes | length' "$CONFIG_FILE")
    
    # Count installed nodes
    while IFS= read -r node_name; do
        if [ -n "$node_name" ] && [ "$node_name" != "null" ]; then
            local node_path="$CUSTOM_NODES_PATH/$node_name"
            if [ -d "$node_path" ]; then
                installed_count=$((installed_count + 1))
                log "✅ $node_name verified"
            else
                log "❌ $node_name not found"
            fi
        fi
    done <<< "$(jq -r '.installation_order[]' "$CONFIG_FILE")"
    
    log "📊 Installation summary: $installed_count/$total_count nodes installed"
    
    if [ "$installed_count" -eq "$total_count" ]; then
        log "🎉 All custom nodes installed successfully!"
        return 0
    else
        log "⚠️ Some nodes failed to install"
        return 1
    fi
}

# Main execution
main() {
    log "🚀 ComfyUI Custom Nodes Installer"
    log "Config: $CONFIG_FILE"
    log "ComfyUI Path: $COMFYUI_PATH"
    log "Custom Nodes Path: $CUSTOM_NODES_PATH"
    
    check_dependencies
    check_config
    install_all_nodes
    run_post_install
    verify_installation
    
    log "✨ Custom nodes installation complete!"
}

# Run main function
main "$@"