# Codex Environment Setup Guide

## 🎯 Overview

This document describes how to set up the RunPod ComfyUI Serverless repo in the Codex environment.

## 🚀 Quick Start

### In Codex Web UI:

1. **Insert Setup Script:**
   - Go to Codex → "Setup Script"
   - Select "Manual"
   - Paste the following command:

```bash
# Codex Setup for RunPod ComfyUI Serverless
curl -fsSL https://raw.githubusercontent.com/EcomTree/runpod-comfyui-serverless/main/scripts/setup.sh | bash
```

OR (if you want to test a branch):

```bash
# Run Setup Script
git clone https://github.com/EcomTree/runpod-comfyui-serverless.git /workspace/runpod-comfyui-serverless
cd /workspace/runpod-comfyui-serverless
bash scripts/setup.sh
```

2. **Set Environment Variables (Optional):**
   - Click on "Environment Variables" → "Add"
   - Add the following variables if you want to use S3:

   | Variable | Value | Description |
   |----------|------|--------------|
   | `S3_BUCKET` | `your-bucket-name` | S3 Bucket for images |
   | `S3_ACCESS_KEY` | `xxx` | S3 Access Key ID |
   | `S3_SECRET_KEY` | `xxx` | S3 Secret Key |
   | `S3_ENDPOINT_URL` | `https://...` | Endpoint (for R2/B2) |
   | `S3_REGION` | `auto` or `us-east-1` | S3 Region |

3. **Start Container:**
   - Enable "Container Caching"
   - Start the environment

## 📦 What Gets Installed?

The setup script automatically installs:

### Python Packages:
- ✅ `runpod` - RunPod SDK
- ✅ `requests` - HTTP Client
- ✅ `boto3` - AWS S3 SDK
- ✅ `Pillow` - Image processing
- ✅ `numpy` - Numerical computations

### System Tools:
- ✅ `jq` - JSON Parser (for debugging)
- ✅ `curl` - HTTP Client

### Already Pre-installed (according to Codex):
- ✅ Python 3.12
- ✅ Node.js 20
- ✅ Ruby 3.4.4
- ✅ Rust 1.89.0
- ✅ Go 1.24.3
- ✅ Bun 1.2.14
- ✅ PHP 8.4
- ✅ Java 21
- ✅ Swift 6.1

## 🔧 Configuration

### Option 1: S3 Storage (Recommended for Codex)

S3 is ideal for Codex as generated images are directly accessible via HTTP URLs:

```bash
# Cloudflare R2 (Free up to 10GB)
S3_BUCKET=comfyui-outputs
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_ENDPOINT_URL=https://account-id.r2.cloudflarestorage.com
S3_REGION=auto
```

### Option 2: Network Volume (only in RunPod Serverless)

Network Volumes only work in the RunPod Serverless environment, **not in Codex**:

```bash
RUNPOD_VOLUME_PATH=/runpod-volume
```

## 🧪 Testing in Codex

After setup, you can test the following in Codex:

```bash
# In Codex Terminal:
cd /workspace/runpod-comfyui-serverless

# Test Python Handler (Syntax Check)
python3 -m py_compile rp_handler.py

# Check Dependencies
python3 -c "import runpod, requests, boto3; print('✅ All dependencies available')"

# Prepare test script
chmod +x test_endpoint.sh
```

## 📝 Maintenance Script

The setup script is also referenced in the Dockerfile as "maintenance script".

**For RunPod Serverless Container:**

```dockerfile
# Optionally add to Dockerfile:
COPY scripts/setup.sh /workspace/setup.sh
RUN chmod +x /workspace/setup.sh && /workspace/setup.sh
```

## 🐛 Troubleshooting

### "Connection Error" in Codex Terminal

This is normal on first start. The setup script creates the necessary structure automatically.

### "Volume not ready"

In Codex there are no RunPod Network Volumes. Use S3 Storage instead.

### Python Module not found

```bash
# Run setup again:
cd /workspace/runpod-comfyui-serverless
bash scripts/setup.sh
```

## 🎯 Next Steps

After successful setup:

1. **Local Testing:**
   ```bash
   # Test the handler (without ComfyUI)
   python3 -c "from rp_handler import handler; print('✅ Handler importable')"
   ```

2. **Docker Build (for Deployment):**
   ```bash
   docker build -t ecomtree/comfyui-serverless:latest -f Dockerfile .
   ```

3. **RunPod Deployment:**
   - Push the image to Docker Hub
   - Create Serverless Endpoint in RunPod
   - Configure environment variables

## 💡 Tips

- ✅ **Use S3** for easy HTTP access to generated images
- ✅ **Cloudflare R2** is free up to 10GB (perfect for testing)
- ✅ **Enable Container Caching** in Codex for faster starts
- ✅ **Setup Script** can be run multiple times (idempotent)

## 🆘 Support

For questions or problems:
- Check the logs: `cat /workspace/logs/*.log`
- GitHub Issues: https://github.com/EcomTree/runpod-comfyui-serverless/issues
- RunPod Docs: https://docs.runpod.io/

---

**Created for Codex Environment Setup** 🚀
