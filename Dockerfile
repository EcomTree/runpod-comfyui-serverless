# syntax=docker/dockerfile:1.4
# Multi-stage Dockerfile for optimized ComfyUI Serverless deployment

# ============================================================
# Stage 1: Builder - Dependencies and ComfyUI setup
# ============================================================
FROM runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04 AS builder

# Build arguments for dynamic versioning
ARG COMFYUI_VERSION=v0.3.57
ARG INSTALL_CUSTOM_NODES=true
ARG ENABLE_OPTIMIZATIONS=true

# Environment for build
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System packages with BuildKit cache mount for faster rebuilds
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
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
        libgomp1 && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /workspace

# Copy only requirements first for better layer caching
COPY requirements.txt /workspace/requirements.txt

# Install Python dependencies with pip cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY scripts/ /workspace/scripts/
COPY src/ /workspace/src/
COPY configs/ /workspace/configs/
COPY models_download.json /workspace/models_download.json

# Make scripts executable
RUN chmod +x /workspace/scripts/*.sh && \
    chmod +x /workspace/scripts/*.py

# Clone ComfyUI with dynamic version
RUN echo "📦 Installing ComfyUI ${COMFYUI_VERSION}" && \
    git clone https://github.com/comfyanonymous/ComfyUI.git && \
    cd ComfyUI && \
    git checkout ${COMFYUI_VERSION} && \
    echo "✅ ComfyUI ${COMFYUI_VERSION} installed"

# Install ComfyUI dependencies (excluding torch which is in base image)
WORKDIR /workspace/ComfyUI
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir $(grep -v -E "^torch([^a-z]|$)|torchvision|torchaudio" requirements.txt | grep -v "^#" | grep -v "^$" | tr '\n' ' ') && \
    pip install --no-cache-dir librosa soundfile av moviepy

# Install custom nodes using automated installer
RUN if [ "$INSTALL_CUSTOM_NODES" = "true" ]; then \
        echo "📦 Installing custom nodes..." && \
        /workspace/scripts/install_custom_nodes.sh install && \
        echo "✅ Custom nodes installed"; \
    else \
        echo "⏩ Skipping custom nodes installation"; \
    fi

# Create model directories
RUN mkdir -p /workspace/ComfyUI/models/checkpoints \
             /workspace/ComfyUI/models/clip \
             /workspace/ComfyUI/models/vae \
             /workspace/ComfyUI/models/unet \
             /workspace/ComfyUI/models/loras \
             /workspace/ComfyUI/models/clip_vision \
             /workspace/ComfyUI/models/text_encoders \
             /workspace/ComfyUI/models/diffusion_models \
             /workspace/ComfyUI/models/controlnet \
             /workspace/ComfyUI/models/upscale_models \
             /workspace/ComfyUI/models/embeddings \
             /workspace/ComfyUI/models/animatediff_models \
             /workspace/ComfyUI/output \
             /workspace/logs \
             /workspace/outputs && \
    echo "✅ Directory structure created"

# ============================================================
# Stage 2: Runtime - Final optimized image
# ============================================================
FROM runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04

# Metadata
LABEL maintainer="Sebastian" \
      description="ComfyUI Serverless Worker - Optimized Multi-Stage Build" \
      version="3.0" \
      comfyui.version="${COMFYUI_VERSION:-v0.3.57}" \
      features="dynamic-versioning,performance-optimizations,multi-stage-build,custom-nodes"

# Runtime environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512,expandable_segments:True \
    TORCH_ALLOW_TF32_CUBLAS_OVERRIDE=1 \
    PYTORCH_JIT=1 \
    PYTHONPATH=/workspace:/workspace/src \
    COMFYUI_PATH=/workspace/ComfyUI

# Install only runtime dependencies (minimal layer)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        curl \
        jq \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libgomp1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy installed dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/dist-packages /usr/local/lib/python3.11/dist-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy workspace from builder
WORKDIR /workspace
COPY --from=builder /workspace /workspace

# Copy handler
COPY rp_handler.py /workspace/rp_handler.py

# Apply performance optimizations at build time
RUN python3 /workspace/scripts/optimize_performance.py --check || true

# Create version info file
RUN echo "{\
  \"comfyui_version\": \"${COMFYUI_VERSION:-v0.3.57}\",\
  \"build_date\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\
  \"pytorch_version\": \"$(python3 -c 'import torch; print(torch.__version__)')\",\
  \"cuda_version\": \"$(python3 -c 'import torch; print(torch.version.cuda)')\",\
  \"optimizations\": \"torch.compile,tf32,cudnn_benchmark\"\
}" > /workspace/build_info.json && \
    cat /workspace/build_info.json

# Health check with faster interval for serverless
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=2 \
    CMD python3 -c "import requests; requests.get('http://127.0.0.1:8188/system_stats', timeout=3)" || exit 1

# Expose ComfyUI port
EXPOSE 8188

# Start command
CMD ["python3", "-u", "/workspace/rp_handler.py"]
