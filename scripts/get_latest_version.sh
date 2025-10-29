#!/bin/bash

# Get latest ComfyUI version from GitHub API
# Usage: ./get_latest_version.sh [--tag] [--commit] [--prerelease]
# Default: returns latest stable release tag

set -e

# GitHub API endpoint for ComfyUI releases
API_URL="https://api.github.com/repos/comfyanonymous/ComfyUI/releases"

# Parse command line arguments
INCLUDE_PRERELEASE=false
OUTPUT_TYPE="tag"

while [[ $# -gt 0 ]]; do
    case $1 in
        --tag)
            OUTPUT_TYPE="tag"
            shift
            ;;
        --commit)
            OUTPUT_TYPE="commit"
            shift
            ;;
        --prerelease)
            INCLUDE_PRERELEASE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--tag] [--commit] [--prerelease]"
            echo "  --tag        Output version tag (default)"
            echo "  --commit     Output commit hash"
            echo "  --prerelease Include pre-releases"
            echo "  --help       Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Function to get latest version
get_latest_version() {
    local url="$API_URL"
    if [ "$INCLUDE_PRERELEASE" = false ]; then
        url="${url}?per_page=1"
    else
        url="${url}?per_page=10"
    fi
    
    # Get releases and filter for stable releases if needed
    local releases
    if [ "$INCLUDE_PRERELEASE" = false ]; then
        releases=$(curl -s "$url" | jq -r '.[0]')
    else
        # Get first non-prerelease or first release if all are prereleases
        releases=$(curl -s "$url" | jq -r '.[] | select(.prerelease == false) | .' | head -n 1)
        if [ -z "$releases" ] || [ "$releases" = "null" ]; then
            # Fallback to first release if no stable releases found
            releases=$(curl -s "$url" | jq -r '.[0]')
        fi
    fi
    
    if [ -z "$releases" ] || [ "$releases" = "null" ]; then
        echo "Error: Could not fetch ComfyUI releases" >&2
        exit 1
    fi
    
    case $OUTPUT_TYPE in
        "tag")
            echo "$releases" | jq -r '.tag_name'
            ;;
        "commit")
            echo "$releases" | jq -r '.target_commitish'
            ;;
        *)
            echo "Error: Unknown output type: $OUTPUT_TYPE" >&2
            exit 1
            ;;
    esac
}

# Check dependencies
if ! command -v curl &> /dev/null; then
    echo "Error: curl is required but not installed" >&2
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed" >&2
    exit 1
fi

# Get and output the latest version
get_latest_version