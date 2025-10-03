FROM runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04

# ------------------------------------------------------------
# Metadata
# ------------------------------------------------------------
LABEL maintainer="Sebastian" \
      description="ComfyUI H200 – Runpod Serverless Worker"

# ------------------------------------------------------------
# System Packages
# ------------------------------------------------------------
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y git wget curl unzip && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# ------------------------------------------------------------
# Python Dependencies
# ------------------------------------------------------------
COPY requirements.txt /workspace/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /workspace/requirements.txt && \
    pip install --no-cache-dir pyyaml scipy opencv-python

# ------------------------------------------------------------
# ComfyUI Checkout (headless)
# ------------------------------------------------------------
WORKDIR /workspace
RUN git clone https://github.com/comfyanonymous/ComfyUI.git && \
    cd ComfyUI && git checkout v0.3.57 && \
    pip install --no-cache-dir $(grep -v -E "^torch([^a-z]|$)|torchvision|torchaudio" requirements.txt | grep -v "^#" | grep -v "^$" | tr '\n' ' ') && \
    pip install --no-cache-dir librosa soundfile av moviepy

# ------------------------------------------------------------
# Volume Model Setup - Models come from S3 Network Volume
# ------------------------------------------------------------
# Create empty Model Directories for ComfyUI
RUN mkdir -p /workspace/ComfyUI/models/checkpoints && \
    mkdir -p /workspace/ComfyUI/models/clip && \
    mkdir -p /workspace/ComfyUI/models/vae && \
    mkdir -p /workspace/ComfyUI/models/unet && \
    mkdir -p /workspace/ComfyUI/models/loras && \
    mkdir -p /workspace/ComfyUI/output && \
    echo "📦 Model Directories created"

# ------------------------------------------------------------
# Copy Worker Handler
# ------------------------------------------------------------
COPY rp_handler.py /workspace/rp_handler.py

# ------------------------------------------------------------
# Runtime Env Vars
# ------------------------------------------------------------
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024,expandable_segments:True \
    TORCH_ALLOW_TF32_CUBLAS_OVERRIDE=1

# ------------------------------------------------------------
# Start the Runpod Serverless Worker
# ------------------------------------------------------------
CMD ["python3", "-u", "/workspace/rp_handler.py"]
