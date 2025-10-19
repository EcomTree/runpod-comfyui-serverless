FROM runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04

# ------------------------------------------------------------
# Metadata
# ------------------------------------------------------------
LABEL maintainer="Sebastian" \
      description="ComfyUI Serverless Worker - Modular Architecture" \
      version="2.0"

# ------------------------------------------------------------
# Environment Variables
# ------------------------------------------------------------
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ------------------------------------------------------------
# System Packages
# ------------------------------------------------------------
RUN apt-get update && \
    apt-get install -y \
        git \
        wget \
        curl \
        unzip \
        build-essential \
        software-properties-common \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# ------------------------------------------------------------
# Python Setup
# ------------------------------------------------------------
# Upgrade pip and install core tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy project files
WORKDIR /workspace
COPY requirements.txt /workspace/requirements.txt
COPY scripts/ /workspace/scripts/
COPY src/ /workspace/src/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------
# ComfyUI Installation
# ------------------------------------------------------------
# Clone and setup ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git && \
    cd ComfyUI && \
    git checkout v0.3.57

# Install ComfyUI dependencies (excluding torch/torchvision/torchaudio which are in base image)
WORKDIR /workspace/ComfyUI
RUN pip install --no-cache-dir $(grep -v -E "^torch([^a-z]|$)|torchvision|torchaudio" requirements.txt | grep -v "^#" | grep -v "^$" | tr '\n' ' ')

# Install additional ComfyUI packages
RUN pip install --no-cache-dir librosa soundfile av moviepy

# ------------------------------------------------------------
# Custom Nodes Installation
# ------------------------------------------------------------
# Install LoadImageFromHttpURL custom node
RUN mkdir -p /workspace/ComfyUI/custom_nodes && \
    cd /workspace/ComfyUI/custom_nodes && \
    git clone https://github.com/jerrywap/ComfyUI_LoadImageFromHttpURL.git && \
    cd ComfyUI_LoadImageFromHttpURL && \
    if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    fi

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

# ------------------------------------------------------------
# Copy Application Code
# ------------------------------------------------------------
COPY rp_handler.py /workspace/rp_handler.py

# Make scripts executable
RUN chmod +x /workspace/scripts/*.sh

# ------------------------------------------------------------
# Runtime Configuration
# ------------------------------------------------------------
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024,expandable_segments:True \
    TORCH_ALLOW_TF32_CUBLAS_OVERRIDE=1 \
    PYTHONPATH=/workspace:/workspace/src

# ------------------------------------------------------------
# Health Check
# ------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://127.0.0.1:8188/system_stats', timeout=5)" || exit 1

# ------------------------------------------------------------
# Start Command
# ------------------------------------------------------------
CMD ["python3", "-u", "/workspace/rp_handler.py"]
