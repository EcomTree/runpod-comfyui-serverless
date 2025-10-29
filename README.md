# RunPod ComfyUI Serverless Handler

A high-performance serverless handler for running ComfyUI image & video workflows on RunPod's Serverless GPU Infrastructure with S3 storage support.

> **⚠️ CUDA 12.8 Required**: This image only works on **Ada Lovelace** (RTX 40xx, L40), **Hopper** (H100/H200), or **Blackwell** GPUs. Older Ampere GPUs (RTX 30xx, A100) are NOT supported!

## 🚀 Features

- **Serverless GPU Computing**: Uses RunPod's Serverless Platform for scalable GPU computations
- **ComfyUI Integration**: Seamless integration with ComfyUI for AI image & video generation
- **Heavy Video Rendering**: Optimized for long-running video workflows (AnimateDiff, SVD, etc.)
- **Automatic Seed Randomization**: Seeds are automatically randomized for each execution (configurable)
- **S3 Storage**: Direct upload to Cloudflare R2, AWS S3, or Backblaze B2 with presigned URLs
- **RunPod Network Volume Support**: Automatic backup of generated files to RunPod Network Volume
- **Workflow Flexibility**: Supports both predefined and dynamic workflows
- **Extended Timeouts**: 20 min startup timeout, 60 min workflow execution timeout
- **Error Handling**: Robust error handling and detailed logging with automatic stderr output
 - **Dynamic ComfyUI Versioning**: Build with latest or a specific tag via Docker ARG
 - **Performance Tuning**: TF32, cuDNN autotune, and optional `torch.compile`
 - **Custom Nodes Pack**: 5+ essential custom nodes pre-installed (configurable)
 - **Model Downloader**: Parallel downloads with checksum verification
 - **Multi-stage Docker Build**: Smaller images and faster rebuilds using BuildKit caches

## 📋 Requirements

- RunPod Account with API Key
- RunPod Network Volume (for persistent storage)
- Docker (for image build)
- Python 3.11+

### 🔥 GPU Requirements (CUDA 12.8)

**⚠️ IMPORTANT: This image requires CUDA 12.8 or higher!**

Only GPUs with **Ada Lovelace, Hopper, or Blackwell architecture** are supported:

#### ✅ Compatible GPUs (CUDA 12.8+):
- **Consumer/Prosumer:**
  - RTX 4090, RTX 4080, RTX 4070 Ti (Ada Lovelace)
  - RTX 5090, RTX 5080 (Blackwell - when available)
  
- **Datacenter:**
  - L40, L40S (Ada Lovelace)
  - H100, H200 (Hopper)
  - B100, B200 (Blackwell)

#### ❌ NOT Compatible (Older Architectures):
- **RTX 3090, RTX 3080, A100, A40** (Ampere) - Will NOT work!
- All older GPUs (Turing, Pascal, etc.)

**How to filter in RunPod:**
1. Go to RunPod → Serverless → Deploy Endpoint
2. Filter by "CUDA 12.8" or "CUDA 12.9"
3. Only select GPUs from the compatible list above

#### 💾 VRAM Recommendations by Workload:
- **Images (SD 1.5/SDXL)**: 16GB+ (RTX 4080, L40)
- **Videos (AnimateDiff, SVD)**: 24GB+ (RTX 4090, L40S)
- **Heavy Video (4K, long sequences)**: 48GB+ (H100, H200)

## 🛠️ Installation

> **Quick Setup:**
>
> ```bash
> # Download and run the unified setup script
> curl -fsSL https://raw.githubusercontent.com/EcomTree/runpod-comfyui-serverless/main/scripts/setup.sh | bash
> ```

1. **Clone Repository**
   ```bash
   git clone https://github.com/EcomTree/runpod-comfyui-serverless.git
   cd runpod-comfyui-serverless
   ```

2. **Setup Environment**
   ```bash
   # Run the setup script for automatic configuration
   bash scripts/setup.sh
   ```

3. **Build Docker Image**
   ```bash
   # Build with latest ComfyUI release (default)
   docker build -t ecomtree/comfyui-serverless:latest -f Dockerfile .

   # Or pin a specific ComfyUI version
   docker build --build-arg COMFYUI_VERSION=v0.3.57 \
     -t ecomtree/comfyui-serverless:0.3.57 -f Dockerfile .
   ```

4. **Push Image to Docker Hub**
   ```bash
   docker push ecomtree/comfyui-serverless:latest
   ```

## 🔧 Configuration

### Environment Variables

The handler supports the following environment variables:

#### ComfyUI Configuration
- `COMFY_PORT`: ComfyUI Port (default: 8188)
- `COMFY_HOST`: ComfyUI Host (default: 127.0.0.1)
- `RANDOMIZE_SEEDS`: Automatically randomize all seeds in workflows (default: true)
  - Set to `false` if you want to preserve exact seeds from your workflow
  - When enabled, all seed values are replaced with random values before execution

#### Performance Tuning
- `ENABLE_TORCH_COMPILE`: Enable torch.compile optimization hooks (default: false)
- `TORCH_COMPILE_BACKEND`: Compile backend (default: inductor)
- `TORCH_COMPILE_MODE`: default | reduce-overhead (default) | max-autotune
- `TORCH_COMPILE_FULLGRAPH`: Require full graph capture (default: 0)
- `TORCH_COMPILE_DYNAMIC`: Allow dynamic shapes (default: 0)
- `ENABLE_TF32`: Allow TF32 on Ampere+ (default: true)
- `ENABLE_CUDNN_BENCHMARK`: Enable cuDNN autotune (default: true)
- `MATMUL_PRECISION`: highest | high (default) | medium
- `COMFY_EXTRA_ARGS`: Extra CLI flags passed to ComfyUI at startup

See `docs/performance-tuning.md` for details.

#### Storage Configuration (S3 or Network Volume)

**S3 Storage (Recommended for HTTP Access):**
- `S3_BUCKET`: Name of your S3 Bucket (required)
- `S3_ACCESS_KEY`: S3 Access Key ID (required)
- `S3_SECRET_KEY`: S3 Secret Access Key (required)
- `S3_ENDPOINT_URL`: Custom Endpoint for S3-compatible services (e.g. Cloudflare R2, Backblaze B2)
- `S3_REGION`: S3 Region (default: "auto")
- `S3_PUBLIC_URL`: Optional: Custom Public URL Prefix (e.g. CDN URL)
- `S3_SIGNED_URL_EXPIRY`: Validity duration of signed URLs in seconds (default: 3600)

**Network Volume (Fallback):**
- `RUNPOD_VOLUME_PATH`: Path to Network Volume (default: /runpod-volume)
- `RUNPOD_OUTPUT_DIR`: Alternative output directory (optional)
- `VOLUME_MODELS_DIR`: Optional override path to models directory (if nonstandard)

**Note:** When S3 is configured, it will be used automatically. The Network Volume serves as fallback.

#### Debugging & Logging
- `DEBUG_S3_URLS`: Log full presigned URLs including authentication tokens (default: false)
  - **⚠️ Security Warning:** Only enable in development! Presigned URLs contain sensitive tokens
  - When disabled, URLs in logs show path only with note: `[presigned - query params redacted for security]`
  - See [URL_LOGGING.md](./URL_LOGGING.md) for detailed information

### Workflow Configuration

Workflows are passed as JSON directly in the request. The handler expects the ComfyUI workflow format.

### Model Downloads (Optional)

This project includes a model downloader with link verification and checksum validation.

```bash
# Verify links (skips auth-only links unless HUGGINGFACE_TOKEN is set)
python scripts/verify_links.py --config models_download.json

# Download a subset of models (e.g., checkpoints and vae)
python scripts/download_models.py --config models_download.json \
  --categories checkpoints,vae --concurrency 4

# Optionally set a Hugging Face token for gated models
export HUGGINGFACE_TOKEN=hf_xxx
```

Manifest format: see `models_download.json`.

## 📝 Usage

### Request Format

```json
{
  "input": {
    "workflow": {
      // ComfyUI Workflow JSON
      // Example: SD 1.5 Text-to-Image
      "3": {
        "inputs": {
          "seed": 42,
          "steps": 20,
          "cfg": 7.0,
          "sampler_name": "euler",
          "scheduler": "normal",
          "denoise": 1.0,
          "model": ["4", 0],
          "positive": ["6", 0],
          "negative": ["7", 0],
          "latent_image": ["5", 0]
        },
        "class_type": "KSampler"
      }
      // ... more nodes
    }
  }
}
```

### Response Format

**With S3 Storage (Cloudflare R2, AWS S3, Backblaze B2):**
```json
{
  "links": [
    "https://account-id.r2.cloudflarestorage.com/comfyui-outputs/job-id/20251003_120530_output_image.png?X-Amz-..."
  ],
  "total_images": 1,
  "job_id": "abc123",
  "storage_type": "s3",
  "s3_bucket": "comfyui-outputs",
  "local_paths": [
    "/workspace/ComfyUI/output/output_image.png"
  ],
  "volume_paths": [
    "/runpod-volume/comfyui/output/comfyui-20251003_120530_000000-abc12345-output_image.png"
  ]
}
```

**With Network Volume Only (S3 not configured):**
```json
{
  "links": [
    "/runpod-volume/comfyui/output/comfyui-20251003_120530_000000-abc12345-output_image.png"
  ],
  "total_images": 1,
  "job_id": "abc123",
  "storage_type": "volume",
  "volume_paths": [
    "/runpod-volume/comfyui/output/comfyui-20251003_120530_000000-abc12345-output_image.png"
  ]
}
```

**Note:** When S3 is configured, images are uploaded to S3 **and** backed up to the Network Volume. The `links` array contains publicly accessible S3 URLs (presigned URLs by default, or custom CDN URLs if `S3_PUBLIC_URL` is set).

## ☁️ S3 Setup Guide

### Cloudflare R2 (Recommended - Free up to 10GB)

1. **Create R2 Bucket:**
   - Go to [Cloudflare Dashboard](https://dash.cloudflare.com/) → R2
   - Create new bucket (e.g. `comfyui-outputs`)

2. **Create API Token:**
   - R2 → Manage R2 API Tokens → Create API Token
   - Note down: Access Key ID, Secret Access Key
   - Endpoint URL: `https://<account-id>.r2.cloudflarestorage.com`

3. **Set Environment Variables in RunPod:**
   ```
   S3_BUCKET=comfyui-outputs
   S3_ACCESS_KEY=<your-access-key>
   S3_SECRET_KEY=<your-secret-key>
   S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
   S3_REGION=auto
   ```

### AWS S3

1. **Create S3 Bucket:**
   - [AWS Console](https://console.aws.amazon.com/s3/) → Create Bucket
   - Select region (e.g. `us-east-1`)

2. **IAM User & Credentials:**
   - IAM → Users → Add User
   - Permissions: `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`

3. **Environment Variables:**
   ```
   S3_BUCKET=your-bucket-name
   S3_ACCESS_KEY=<aws-access-key>
   S3_SECRET_KEY=<aws-secret-key>
   S3_REGION=us-east-1
   ```

### Backblaze B2

1. **Create Bucket:** [Backblaze Console](https://www.backblaze.com/b2/cloud-storage.html)
2. **Create Application Key:** Note down Key ID & Key
3. **Environment Variables:**
   ```
   S3_BUCKET=your-bucket-name
   S3_ACCESS_KEY=<key-id>
   S3_SECRET_KEY=<application-key>
   S3_ENDPOINT_URL=https://s3.us-west-002.backblazeb2.com
   S3_REGION=us-west-002
   ```

## 🧪 Testing

Use the included test script to validate your endpoint:

```bash
# Configure the test script
cp scripts/test_endpoint.sh scripts/test_endpoint_local.sh
# Edit scripts/test_endpoint_local.sh with your ENDPOINT_ID and API_KEY

# Run tests
bash scripts/test_endpoint_local.sh
```

**Note**: Never commit API keys or endpoint IDs to version control!

```bash
#!/bin/bash
# WARNING: Do not commit real API keys or endpoint IDs to version control!
ENDPOINT_ID="your-endpoint-id"
API_KEY="your-runpod-api-key"
API_URL="https://api.runpod.ai/v2/${ENDPOINT_ID}/runsync"

curl -X POST "$API_URL" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "workflow": "workflow_data_here"
    }
  }'
```

## 🏗️ Architecture

```
runpod-comfyui-serverless/
├── src/                           # Source code modules
│   ├── config.py                  # Configuration management
│   ├── comfyui_manager.py         # ComfyUI server lifecycle
│   ├── s3_handler.py              # S3 storage operations
│   └── workflow_processor.py      # Workflow processing utilities
├── scripts/                       # Setup and maintenance scripts
│   ├── setup.sh                   # Unified setup script
│   ├── common-codex.sh             # Shared helper functions
│   └── test_endpoint.sh           # Testing utilities
├── config/                        # Configuration files
├── tests/                         # Test files
├── rp_handler.py                  # Main RunPod handler
├── Dockerfile                     # Serverless Docker image
├── requirements.txt               # Python dependencies
├── .env.example                   # Configuration template
├── .gitignore                     # Git ignore rules
└── README.md                      # This file
```

### Handler Architecture

The handler is now organized into focused modules:

- **src/config.py**: Centralized configuration management with environment variable parsing
- **src/comfyui_manager.py**: ComfyUI server lifecycle, workflow execution, and model management
- **src/s3_handler.py**: S3 storage operations with proper error handling and URL sanitization
- **src/workflow_processor.py**: Workflow processing utilities including seed randomization
- **rp_handler.py**: Main entry point that orchestrates all components
 - **scripts/**: Installers, model management, and performance hooks
   - `scripts/get_latest_version.sh`: Resolve latest ComfyUI release
   - `scripts/install_custom_nodes.sh`: Install core custom nodes from `configs/custom_nodes.json`
   - `scripts/download_models.py`: Parallel model downloader with checksums
   - `scripts/verify_links.py`: Link validation tool
 - **docs/**: Guides for performance tuning and custom nodes

## 🚀 Deployment

1. **Setup and Build**
   ```bash
   # Clone and setup the project
   git clone https://github.com/EcomTree/runpod-comfyui-serverless.git
   cd runpod-comfyui-serverless
   bash scripts/setup.sh

   # Build Docker image
   docker build -t ecomtree/comfyui-serverless:latest -f Dockerfile .
   docker push ecomtree/comfyui-serverless:latest
   ```

2. **Create RunPod Serverless Endpoint**
   - Go to [RunPod Dashboard](https://runpod.io/console/serverless)
   - Create new Serverless Endpoint
   - **Docker Image**: `ecomtree/comfyui-serverless:latest`
   - **Container Disk**: at least 15GB (20GB recommended for large models)
   - **GPU Filter**: CUDA 12.8 or 12.9 only!
   - **GPU**: RTX 4090, L40/L40S, H100/H200 or better (see GPU Requirements above)
   - **Important**: Connect Network Volume with sufficient storage for models and outputs

3. **Configure Environment Variables**
   Set the following environment variables in your RunPod endpoint:
   ```bash
   # S3 Storage (recommended)
   S3_BUCKET=your-bucket-name
   S3_ACCESS_KEY=your-access-key
   S3_SECRET_KEY=your-secret-key
   S3_ENDPOINT_URL=https://your-s3-endpoint.com

   # Performance tuning
   PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024,expandable_segments:True
   TORCH_ALLOW_TF32_CUBLAS_OVERRIDE=1
   ```

4. **Note down credentials**
   - **Endpoint ID**: Available in the RunPod dashboard
   - **API Key**: Generated when creating the endpoint

## 📊 Performance

- **Cold Start**: ~15-30 seconds (ComfyUI + Model Loading)
- **Heavy Model Loading**: Up to 20 minutes for large model collections
- **Warm Start**: ~2-5 seconds
- **Image Workflow**: 5-120 seconds (depends on model and settings)
- **Video Workflow**: 2-60 minutes (depends on frames, resolution, and models)
- **S3 Upload**: ~1-5 seconds per file
- **Volume Save**: <1 second per file

## 💡 Technical Details

- **Base Image**: `runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04`
- **CUDA Version**: 12.8.1 (requires Ada Lovelace, Hopper, or Blackwell GPUs)
- **ComfyUI Version**: dynamic (default: latest release)
- **PyTorch**: 2.8.0 with CUDA 12.8
- **Custom Nodes**: Manager, Impact-Pack, rgthree-comfy, Advanced-ControlNet, VideoHelperSuite, LoadImageFromHttpURL
- **GPU Memory**: Optimized with `--normalvram` flag
- **Tensor Cores**: Fully optimized for modern Tensor Cores (4th gen+)

Build is multi-stage and uses BuildKit cache mounts for faster rebuilds.

## 🤝 Contributing

Contributions are welcome! Please create a pull request with your changes.

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- [RunPod](https://runpod.io) for the Serverless GPU Infrastructure
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) for the awesome AI Workflow System
- The Open Source Community for continuous support

---

Created with ❤️ for the AI Art Community
