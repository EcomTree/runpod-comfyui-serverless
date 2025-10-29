# syntax=docker/dockerfile:1
# Multi-stage build for optimized ComfyUI Serverless deployment

# ============================================================
# Stage 1: Base System Setup
# ============================================================
FROM runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04 AS base

# Metadata
LABEL maintainer="Sebastian" \
      description="ComfyUI Serverless Worker - Optimized Multi-Stage Build" \
      version="3.0"

# Environment Variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024,expandable_segments:True \
    TORCH_ALLOW_TF32_CUBLAS_OVERRIDE=1 \
    TORCH_CUDNN_V8_API_ENABLED=1 \
    CUDNN_BENCHMARK=1 \
    CUDNN_DETERMINISTIC=0 \
    CUDNN_CONV_ALGO_WORKSPACE_LIMIT=1024

# System packages with BuildKit cache mount
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

# ============================================================
# Stage 2: Python Dependencies
# ============================================================
FROM base AS python-deps

# Upgrade pip with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements first for better layer caching
COPY requirements.txt /workspace/requirements.txt

# Install Python dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# ============================================================
# Stage 3: ComfyUI Installation
# ============================================================
FROM python-deps AS comfyui-base

# Build arguments for dynamic versioning
ARG COMFYUI_VERSION=latest
ARG ENABLE_PERFORMANCE_OPTIMIZATIONS=true

# Get ComfyUI version dynamically if not specified
RUN if [ "$COMFYUI_VERSION" = "latest" ]; then \
        COMFYUI_VERSION=$(curl -s https://api.github.com/repos/comfyanonymous/ComfyUI/releases/latest | jq -r '.tag_name'); \
    fi && \
    echo "ComfyUI Version: $COMFYUI_VERSION" > /tmp/comfyui_version.txt

# Clone ComfyUI with specific version
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /workspace/ComfyUI && \
    cd /workspace/ComfyUI && \
    COMFYUI_VERSION=$(cat /tmp/comfyui_version.txt | cut -d' ' -f3) && \
    git checkout "$COMFYUI_VERSION" && \
    echo "✅ ComfyUI $COMFYUI_VERSION installed"

# Install ComfyUI dependencies
WORKDIR /workspace/ComfyUI
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir $(grep -v -E "^torch([^a-z]|$)|torchvision|torchaudio" requirements.txt | grep -v "^#" | grep -v "^$" | tr '\n' ' ')

# Install additional ComfyUI packages
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir librosa soundfile av moviepy

# ============================================================
# Stage 4: Custom Nodes Installation
# ============================================================
FROM comfyui-base AS custom-nodes

# Copy custom nodes configuration and scripts
COPY configs/custom_nodes.json /workspace/configs/custom_nodes.json
COPY scripts/install_custom_nodes.sh /workspace/scripts/install_custom_nodes.sh

# Install custom nodes
RUN chmod +x /workspace/scripts/install_custom_nodes.sh && \
    /workspace/scripts/install_custom_nodes.sh --comfyui-path /workspace/ComfyUI

# ============================================================
# Stage 5: Performance Optimizations
# ============================================================
FROM custom-nodes AS optimized

# Copy performance optimization script
COPY scripts/optimize_performance.py /workspace/scripts/optimize_performance.py

# Apply performance optimizations
RUN chmod +x /workspace/scripts/optimize_performance.py && \
    python3 /workspace/scripts/optimize_performance.py --comfyui-path /workspace/ComfyUI

# ============================================================
# Stage 6: Final Runtime Image
# ============================================================
FROM optimized AS runtime

# Copy application code and scripts
COPY src/ /workspace/src/
COPY scripts/ /workspace/scripts/
COPY rp_handler.py /workspace/rp_handler.py

# Make all scripts executable
RUN chmod +x /workspace/scripts/*.sh /workspace/scripts/*.py

# Create directory structure
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

# Set Python path
ENV PYTHONPATH=/workspace:/workspace/src

# Health check with optimized timeout
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://127.0.0.1:8188/system_stats', timeout=5)"

# Expose port
EXPOSE 8188

# Start command
CMD ["python3", "-u", "/workspace/rp_handler.py"]
