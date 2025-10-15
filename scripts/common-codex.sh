#!/bin/bash

# Shared helpers for Codex setup scripts.

if [[ -z "${CODEX_COMMON_HELPERS_LOADED:-}" ]]; then
    CODEX_COMMON_HELPERS_LOADED=1

    GREEN='\033[0;32m'
    BLUE='\033[0;34m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    NC='\033[0m'

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

            echo_warning "Attempt ${attempt}/${max_attempts} failed – retrying in ${delay}s"
            sleep "$delay"
            attempt=$((attempt + 1))
        done
    }

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

    resolve_path() {
        local path="$1"
        if [[ -z "$path" ]]; then
            return 1
        fi
        if [[ "$path" == /* ]]; then
            printf '%s\n' "$path"
        else
            printf '%s/%s\n' "$(pwd)" "$path"
        fi
    }

    is_codex_environment() {
        [ -n "${CODEX_CONTAINER:-}" ] || \
        [ -n "${RUNPOD_POD_ID:-}" ] || \
        [ -n "${CODEX_WORKSPACE:-}" ] || \
        [ -d "/workspace" ]
    }
fi

