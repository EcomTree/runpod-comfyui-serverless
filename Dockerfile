# syntax=docker/dockerfile:1.6
FROM runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04 AS builder

# ------------------------------------------------------------
# Metadata
# ------------------------------------------------------------
LABEL maintainer="Sebastian" \
      description="ComfyUI Serverless Worker - Optimized Multi-Stage Build" \
      version="3.0"

# ------------------------------------------------------------
# Environment Variables
# ------------------------------------------------------------
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ------------------------------------------------------------
# System Packages
# ------------------------------------------------------------
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y \
        git \
        wget \
        curl \
        unzip \
        jq \
        build-essential \
        software-properties-common \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 \
        aiohttp \
        aiofiles && \
    apt-get clean && \
    rm -rf /tmp/* /var/tmp/*

# ------------------------------------------------------------
# Python Setup
# ------------------------------------------------------------
# Upgrade pip and install core tools
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy minimal project files required for building ComfyUI
WORKDIR /workspace
COPY scripts/ /workspace/scripts/
COPY sitecustomize.py /workspace/sitecustomize.py
COPY configs/ /workspace/configs/

# We don't install app requirements in the builder stage

# ------------------------------------------------------------
# ComfyUI Installation (Dynamic Version)
# ------------------------------------------------------------
ARG COMFYUI_REPO="https://github.com/comfyanonymous/ComfyUI.git"
ARG COMFYUI_VERSION="latest"

# Clone and checkout requested ComfyUI version
RUN --mount=type=cache,target=/root/.cache/git bash -lc 'set -euo pipefail; \
    echo "Cloning ComfyUI from: ${COMFYUI_REPO}"; \
    git clone --filter=blob:none "${COMFYUI_REPO}" ComfyUI; \
    cd ComfyUI; \
    VERSION_RESOLVED="${COMFYUI_VERSION}"; \
    if [[ "${COMFYUI_VERSION}" == "latest" ]]; then \
      VERSION_RESOLVED=$(bash /workspace/scripts/get_latest_version.sh) || VERSION_RESOLVED="main"; \
    fi; \
    echo "Using ComfyUI version: ${VERSION_RESOLVED}"; \
    git fetch --tags --depth=1 || true; \
    # Try tag, then branch, finally fallback to main
    if ! git checkout -q "${VERSION_RESOLVED}" 2>/dev/null; then \
      if ! git checkout -q "tags/${VERSION_RESOLVED}" 2>/dev/null; then \
        echo "Falling back to 'main'"; \
        git checkout -q main || git checkout -q master || true; \
      fi; \
    fi'

# Install ComfyUI dependencies (excluding torch/torchvision/torchaudio which are in base image)
WORKDIR /workspace/ComfyUI
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir $(grep -v -E "^torch([^a-z]|$)|torchvision|torchaudio" requirements.txt | grep -v "^#" | grep -v "^$" | tr '\n' ' ')

# Install additional ComfyUI packages
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir librosa soundfile av moviepy

# ------------------------------------------------------------
# Performance Optimizations
# ------------------------------------------------------------
COPY scripts/optimize_performance.py /workspace/scripts/optimize_performance.py
RUN chmod +x /workspace/scripts/optimize_performance.py && \
    python3 /workspace/scripts/optimize_performance.py --comfyui-path /workspace/ComfyUI || true

# ------------------------------------------------------------
# Custom Nodes Installation
# ------------------------------------------------------------
RUN bash /workspace/scripts/install_custom_nodes.sh /workspace/configs/custom_nodes.json

# Reduce repo size by removing git metadata
RUN rm -rf /workspace/ComfyUI/.git

# ------------------------------------------------------------
# Directory Structure
# ------------------------------------------------------------
# Create necessary directories
RUN mkdir -p /workspace/ComfyUI/models/checkpoints && \
    mkdir -p /workspace/ComfyUI/models/clip && \
    mkdir -p /workspace/ComfyUI/models/vae && \
    mkdir -p /workspace/ComfyUI/models/unet && \
    mkdir -p /workspace/ComfyUI/models/loras && \
    mkdir -p /workspace/ComfyUI/models/clip_vision && \
    mkdir -p /workspace/ComfyUI/models/text_encoders && \
    mkdir -p /workspace/ComfyUI/models/diffusion_models && \
    mkdir -p /workspace/ComfyUI/output && \
    mkdir -p /workspace/logs && \
    mkdir -p /workspace/outputs && \
    echo "📦 Project directories created"

# -------------------------------------------
# Runtime Image
# -------------------------------------------
FROM runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04 AS runtime

LABEL maintainer="Sebastian" \
      description="ComfyUI Serverless Worker - Optimized Multi-Stage Build" \
      version="3.0"

# Base environment
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System packages (runtime minimum)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        wget \
        curl \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /workspace

# Copy application files
COPY requirements.txt /workspace/requirements.txt
COPY src/ /workspace/src/
COPY scripts/ /workspace/scripts/
COPY sitecustomize.py /workspace/sitecustomize.py
COPY configs/ /workspace/configs/
COPY rp_handler.py /workspace/rp_handler.py

# Install app dependencies
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir --upgrade pip setuptools wheel && \
    --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir -r requirements.txt

# Copy prepared ComfyUI from builder stage
COPY --from=builder /workspace/ComfyUI /workspace/ComfyUI

# Permissions and executables
RUN chmod +x /workspace/scripts/*.sh || true

# Runtime configuration with performance optimizations
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024,expandable_segments:True \
    TORCH_ALLOW_TF32_CUBLAS_OVERRIDE=1 \
    TORCH_CUDNN_V8_API_ENABLED=1 \
    CUDNN_BENCHMARK=1 \
    CUDNN_DETERMINISTIC=0 \
    CUDNN_CONV_ALGO_WORKSPACE_LIMIT=1024 \
    PYTHONPATH=/workspace:/workspace/src

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://127.0.0.1:8188/system_stats', timeout=5)"

# Expose port
EXPOSE 8188

# Entrypoint
CMD ["python3", "-u", "/workspace/rp_handler.py"]
