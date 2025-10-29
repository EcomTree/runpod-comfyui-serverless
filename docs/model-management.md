# ComfyUI Model Management Guide

Comprehensive guide for downloading, managing, and organizing models for ComfyUI.

## Table of Contents

- [Overview](#overview)
- [Model Categories](#model-categories)
- [Quick Start](#quick-start)
- [Model Packs](#model-packs)
- [Advanced Usage](#advanced-usage)
- [Link Verification](#link-verification)

## Overview

The model management system provides:

- **8 models** across 8 categories
- **Automated downloads** with progress tracking
- **Parallel downloads** for speed
- **Resume support** for interrupted downloads
- **Link verification** tool
- **Pre-configured packs** for common use cases

### Configuration File

Location: `/workspace/models_download.json`

Contains definitions for all available models organized by category.

## Model Categories

### 1. Checkpoints (Main Models)

**Location:** `models/checkpoints/`

**Available Models:**
- SDXL Base 1.0 (6.94 GB)
- SDXL Refiner 1.0 (6.08 GB)
- SD 1.5 Pruned (4.27 GB)
- Realistic Vision V6 (2.13 GB)
- DreamShaper 8 (2.13 GB)
- Juggernaut XL V9 (6.62 GB)

**Example:**
```bash
python3 /workspace/scripts/download_models.py download-category checkpoints
```

### 2. VAE (Variational Autoencoders)

**Location:** `models/vae/`

**Available Models:**
- SDXL VAE (335 MB)
- SD 1.5 VAE (335 MB)

**Purpose:** Improve image quality and color accuracy

### 3. LoRAs (Style Adapters)

**Location:** `models/loras/`

**Available Models:**
- Add Detail (74 MB)
- LCM LoRA SD 1.5 (67 MB)
- LCM LoRA SDXL (393 MB)

**Purpose:** Style transfer and fine-tuning

### 4. ControlNet

**Location:** `models/controlnet/`

**Available Models:**
- Canny Edge (1.45 GB)
- OpenPose (1.45 GB)
- Depth (1.45 GB)
- SDXL Canny (2.50 GB)

**Purpose:** Guided image generation

### 5. Upscale Models

**Location:** `models/upscale_models/`

**Available Models:**
- RealESRGAN x4+ (64 MB)
- RealESRGAN Anime (17 MB)
- UltraSharp x4 (67 MB)

**Purpose:** Image upscaling and enhancement

### 6. CLIP Vision

**Location:** `models/clip_vision/`

**Purpose:** Image understanding for IP-Adapter

### 7. Embeddings

**Location:** `models/embeddings/`

**Available Models:**
- Bad Prompt V2 (26 KB)
- EasyNegative (25 KB)

**Purpose:** Negative prompts and quality control

### 8. AnimateDiff

**Location:** `models/animatediff_models/`

**Available Models:**
- Motion Module SD 1.5 V2 (1.68 GB)
- Motion Module SDXL Beta (950 MB)

**Purpose:** Video generation from images

### 9. UNet (FLUX Models)

**Location:** `models/unet/`

**Available Models:**
- FLUX.1 Dev (23.8 GB)
- FLUX.1 Schnell (23.8 GB)

**Purpose:** Next-gen diffusion models

### 10. CLIP Text Encoders

**Location:** `models/clip/`

**Available Models:**
- CLIP-L (246 MB)
- T5-XXL FP16 (9.13 GB)

**Purpose:** Text encoding for FLUX

## Quick Start

### Download Essential Models

```bash
# Download essential pack (SDXL + VAE + Upscaler)
python3 /workspace/scripts/download_models.py download-pack essential
```

### Download by Category

```bash
# Download all checkpoints
python3 /workspace/scripts/download_models.py download-category checkpoints

# Download all LoRAs
python3 /workspace/scripts/download_models.py download-category loras

# Download all ControlNet models
python3 /workspace/scripts/download_models.py download-category controlnet
```

### Download Specific Model

```bash
python3 /workspace/scripts/download_models.py download-model \
  checkpoints \
  sd_xl_base_1.0.safetensors
```

### List Available Models

```bash
# List all categories
python3 /workspace/scripts/download_models.py list-categories

# List all packs
python3 /workspace/scripts/download_models.py list-packs
```

## Model Packs

Pre-configured model collections for common use cases.

### Essential Pack

**Contents:**
- SDXL Base 1.0
- SDXL VAE
- RealESRGAN x4+

**Use Case:** Basic SDXL image generation

**Download:**
```bash
python3 /workspace/scripts/download_models.py download-pack essential
```

### SD 1.5 Pack

**Contents:**
- SD 1.5 Checkpoint
- SD 1.5 VAE
- Add Detail LoRA
- Canny ControlNet
- OpenPose ControlNet

**Use Case:** Complete SD 1.5 setup

**Download:**
```bash
python3 /workspace/scripts/download_models.py download-pack sd15_pack
```

### SDXL Pack

**Contents:**
- SDXL Base + Refiner
- SDXL VAE
- LCM LoRA SDXL
- SDXL ControlNet

**Use Case:** Full SDXL capabilities

**Download:**
```bash
python3 /workspace/scripts/download_models.py download-pack sdxl_pack
```

### Video Pack

**Contents:**
- SD 1.5 Checkpoint
- AnimateDiff SD 1.5
- AnimateDiff SDXL

**Use Case:** Video generation

**Download:**
```bash
python3 /workspace/scripts/download_models.py download-pack video_pack
```

### FLUX Pack

**Contents:**
- FLUX.1 Schnell
- CLIP-L
- T5-XXL
- SDXL VAE

**Use Case:** Next-gen FLUX models

**Download:**
```bash
python3 /workspace/scripts/download_models.py download-pack flux_pack
```

**Note:** Requires 24GB+ VRAM

## Advanced Usage

### Configuration Options

```bash
# Specify ComfyUI path
python3 /workspace/scripts/download_models.py \
  --comfyui-path /custom/path \
  download-pack essential

# Use custom config
python3 /workspace/scripts/download_models.py \
  --config /custom/models.json \
  download-category checkpoints
```

### Parallel Downloads

**Default:** 3 parallel downloads

**Configure in JSON:**
```json
{
  "download_settings": {
    "parallel_downloads": 5,  // Increase for faster downloads
    "retry_attempts": 3,
    "retry_delay": 5,
    "chunk_size": 8192,
    "resume_downloads": true,
    "timeout": 3600
  }
}
```

### Sequential Downloads

```bash
# Disable parallel downloads
python3 /workspace/scripts/download_models.py \
  download-category checkpoints \
  --sequential
```

### Resume Interrupted Downloads

Downloads automatically resume from where they stopped:

```bash
# Will resume if .part file exists
python3 /workspace/scripts/download_models.py download-category checkpoints
```

### Verify Downloads

```bash
# Verify all downloaded models
python3 /workspace/scripts/download_models.py verify
```

**Output:**
```
✓ checkpoints/sd_xl_base_1.0.safetensors
✓ vae/sdxl_vae.safetensors
✗ loras/add_detail.safetensors

📊 Verification Results:
  ✅ Present: 45
  ❌ Missing: 3
  ⚠️ Corrupt: 0
```

## Link Verification

Verify download links before attempting downloads.

### Verify All Links

```bash
python3 /workspace/scripts/verify_links.py
```

### Verify Category

```bash
python3 /workspace/scripts/verify_links.py --category checkpoints
```

### Verify Pack

```bash
python3 /workspace/scripts/verify_links.py --pack essential
```

### Export Results

```bash
python3 /workspace/scripts/verify_links.py --export results.json
```

### Example Output

```
🔍 Verifying model download links...
============================================================
📊 Total models to verify: 160

✅ checkpoints/sd_xl_base_1.0.safetensors: Size: 6940000000 bytes
✅ vae/sdxl_vae.safetensors: Size: 335000000 bytes
❌ loras/broken_link.safetensors: Connection error
🔄 checkpoints/redirected.safetensors: Redirects to new_url

============================================================
📊 Verification Summary
============================================================
✅ Valid:     157 (98.1%)
❌ Invalid:   2 (1.3%)
⏱️ Timeout:   1 (0.6%)
🔄 Redirect:  0 (0.0%)
📊 Total:     160
```

## Storage Requirements

### By Category

| Category | Count | Total Size |
|----------|-------|------------|
| Checkpoints | 6 | ~29 GB |
| VAE | 2 | ~670 MB |
| LoRAs | 3 | ~534 MB |
| ControlNet | 4 | ~7.85 GB |
| Upscale | 3 | ~148 MB |
| CLIP Vision | 1 | ~2.5 GB |
| Embeddings | 2 | ~51 KB |
| AnimateDiff | 2 | ~2.63 GB |
| UNet (FLUX) | 2 | ~47.6 GB |
| CLIP | 2 | ~9.38 GB |

### By Pack

| Pack | Size | Models |
|------|------|--------|
| Essential | ~7.3 GB | 3 |
| SD 1.5 | ~7.9 GB | 5 |
| SDXL | ~13.6 GB | 5 |
| Video | ~6.3 GB | 3 |
| FLUX | ~33.2 GB | 4 |

## Troubleshooting

### Download Fails

**Check connectivity:**
```bash
curl -I https://huggingface.co/
```

**Verify link:**
```bash
python3 /workspace/scripts/verify_links.py --category checkpoints
```

**Retry with logs:**
```bash
python3 /workspace/scripts/download_models.py download-category checkpoints 2>&1 | tee download.log
```

### Slow Downloads

**Increase parallel downloads:**
Edit `/workspace/models_download.json`:
```json
{
  "download_settings": {
    "parallel_downloads": 5
  }
}
```

**Check bandwidth:**
```bash
# Test download speed
curl -o /dev/null https://huggingface.co/test_file
```

### CivitAI Downloads

Some CivitAI models require API key:

```bash
# Set CivitAI API key
export CIVITAI_API_KEY=your_key_here

# Modify URL in config
"url": "https://civitai.com/api/download/models/12345?token=${CIVITAI_API_KEY}"
```

### HuggingFace Authentication

For gated models:

```bash
# Install huggingface-hub
pip install huggingface-hub

# Login
huggingface-cli login

# Download via CLI
huggingface-cli download model_id
```

### Insufficient Space

**Check space:**
```bash
df -h /workspace
```

**Download selectively:**
```bash
# Download only needed models
python3 /workspace/scripts/download_models.py download-model category model_name
```

## Best Practices

### 1. Start with Packs

Use pre-configured packs for your use case:
```bash
# For general use
python3 /workspace/scripts/download_models.py download-pack essential

# For SD 1.5
python3 /workspace/scripts/download_models.py download-pack sd15_pack
```

### 2. Verify Before Downloading

```bash
# Check links first
python3 /workspace/scripts/verify_links.py

# Then download
python3 /workspace/scripts/download_models.py download-pack essential
```

### 3. Use Resume Feature

For large downloads:
- Downloads resume automatically
- Don't delete `.part` files
- Safe to interrupt and restart

### 4. Monitor Progress

```bash
# Watch download progress
watch -n 2 du -sh /workspace/ComfyUI/models/*/

# Check specific category
watch -n 2 ls -lh /workspace/ComfyUI/models/checkpoints/
```

### 5. Organize by Use Case

Download only what you need:
- SD 1.5 for speed
- SDXL for quality
- FLUX for cutting-edge
- Video for animations

## Adding Custom Models

### 1. Edit Configuration

Add to `/workspace/models_download.json`:

```json
{
  "model_categories": {
    "checkpoints": {
      "models": [
        {
          "name": "my_custom_model.safetensors",
          "url": "https://example.com/model.safetensors",
          "size": "4.27 GB",
          "type": "SD1.5",
          "required": false,
          "priority": 10
        }
      ]
    }
  }
}
```

### 2. Download

```bash
python3 /workspace/scripts/download_models.py download-model checkpoints my_custom_model.safetensors
```

## References

- [Hugging Face Models](https://huggingface.co/models)
- [CivitAI](https://civitai.com/)
- [ComfyUI Model Documentation](https://github.com/comfyanonymous/ComfyUI#models)

## Support

For issues:
1. Verify links: `verify_links.py`
2. Check space: `df -h`
3. Review logs
4. Test individual downloads
