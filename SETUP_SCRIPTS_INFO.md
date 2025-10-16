# Setup Scripts Overview

This repository contains a setup script for Codex Web UI environment configuration.

## 🌐 setup-codex-optimized.sh - For Codex Web UI

**Use this when:** Working with the project in the **Codex Web UI**

### Features:
- ✅ **Fast & lightweight** (~30 seconds)
- ✅ No virtual environment needed (not necessary in Codex)
- ✅ Only essential packages (runpod, requests, boto3, Pillow, numpy)
- ✅ Optimized for pre-installed environment (Python 3.12, Node.js 20, etc.)
- ✅ Creates `.env.example` for configuration

### Usage in Codex:

**Option A - Direct from repo:**
```bash
curl -fsSL https://raw.githubusercontent.com/EcomTree/runpod-comfyui-serverless/main/setup-codex-optimized.sh | bash
```

**Option B - After cloning:**
```bash
git clone https://github.com/EcomTree/runpod-comfyui-serverless.git /workspace/runpod-comfyui-serverless
cd /workspace/runpod-comfyui-serverless
chmod +x setup-codex-optimized.sh
./setup-codex-optimized.sh
```

### Add to Codex Web UI:

Under **"Setup Script"** → **"Manual"**:
```bash
git clone https://github.com/EcomTree/runpod-comfyui-serverless.git /workspace/runpod-comfyui-serverless && cd /workspace/runpod-comfyui-serverless && chmod +x setup-codex-optimized.sh && ./setup-codex-optimized.sh
```

📖 **Complete guide:** See `CODEX_SETUP.md`

---

## 💻 Local Development

For local development on your Mac/PC, you can:

1. **Clone the repository**
   ```bash
   git clone https://github.com/EcomTree/runpod-comfyui-serverless.git
   cd runpod-comfyui-serverless
   ```

2. **Install Python dependencies manually**
   ```bash
   # Create virtual environment (optional but recommended)
   python3 -m venv .venv
   source .venv/bin/activate
   
   # Install core dependencies
   pip install runpod requests boto3 Pillow numpy
   ```

3. **Configure environment**
   ```bash
   # Copy and edit .env
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Test locally**
   ```bash
   # Run handler tests
   python3 -m py_compile rp_handler.py
   
   # Or build Docker image
   docker build -t comfyui-serverless -f Dockerfile .
   ```

---

## 🤔 Which approach should I use?

| Scenario | Approach | Reason |
|----------|----------|--------|
| 🌐 Codex Web UI | `setup-codex-optimized.sh` | Fast, lightweight, optimized for cloud |
| 💻 Local Development | Manual setup | Full control, custom configuration |
| 🐳 Docker Build Only | None needed | Dockerfile has everything |
| 🚀 RunPod Serverless | None needed | Container deployed directly |

---

## 📝 Additional Documentation

- **CODEX_SETUP.md** - Detailed guide for Codex Web UI
- **README.md** - Project overview and usage

---

## 🆘 Troubleshooting

### Codex: "setup-codex-optimized.sh not found"
```bash
# Make sure you're in the right directory:
cd /workspace/runpod-comfyui-serverless
ls -la setup-codex-optimized.sh

# If not present, clone again:
git clone https://github.com/EcomTree/runpod-comfyui-serverless.git
```

### Local: "Permission denied"
```bash
chmod +x setup-codex-optimized.sh
./setup-codex-optimized.sh
```

### "Python version too old"
- **Codex:** Should have Python 3.12 automatically
- **Local:** Install Python 3.11+ from [python.org](https://python.org)

### Missing dependencies
```bash
# In Codex or local:
python3 -m pip install runpod requests boto3 Pillow numpy
```

---

## 🔍 What the setup script does:

1. **Clones repository** (if not in /workspace)
2. **Checks Python version** (Python 3.11+)
3. **Installs dependencies:**
   - runpod - RunPod SDK
   - requests - HTTP client
   - boto3 - AWS S3 SDK
   - Pillow - Image processing
   - numpy - Numerical computing
4. **Installs system tools:**
   - jq - JSON processor
   - curl - HTTP client
5. **Creates `.env.example`** template
6. **Sets up directories:**
   - /workspace/outputs
   - /workspace/logs
7. **Configures git** (if not already configured)
8. **Makes test scripts executable**

---

**Tip:** The script is idempotent - you can run it multiple times safely! ✅
