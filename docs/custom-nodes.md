# ComfyUI Custom Nodes Guide

This guide covers the custom nodes system implemented in the RunPod Serverless ComfyUI deployment.

## Overview

The deployment includes **5 essential custom nodes** that significantly expand ComfyUI's capabilities:

1. **ComfyUI-Manager** - Essential node manager
2. **ComfyUI-Impact-Pack** - Advanced ControlNet and image processing
3. **rgthree-comfy** - Enhanced workflow utilities
4. **ComfyUI-Advanced-ControlNet** - Advanced ControlNet implementations
5. **ComfyUI-VideoHelperSuite** - Video processing and generation

## Installation

### Automatic Installation

Custom nodes are automatically installed during Docker build:

```bash
# Build with custom nodes
docker build -t comfyui-serverless .
```

### Manual Installation

```bash
# Install custom nodes manually
/workspace/scripts/install_custom_nodes.sh

# With custom ComfyUI path
/workspace/scripts/install_custom_nodes.sh --comfyui-path /custom/path

# Verbose output
/workspace/scripts/install_custom_nodes.sh --verbose
```

## Custom Nodes Details

### 1. ComfyUI-Manager

**Purpose**: Essential node manager for ComfyUI
**Repository**: https://github.com/ltdrdata/ComfyUI-Manager.git
**Priority**: 1 (installed first)

**Features:**
- Node installation and management
- Model downloading
- Extension updates
- Dependency management

**Usage:**
- Access via ComfyUI interface
- Automatic dependency resolution
- Model download integration

### 2. ComfyUI-Impact-Pack

**Purpose**: Advanced ControlNet and image processing nodes
**Repository**: https://github.com/ltdrdata/ComfyUI-Impact-Pack.git
**Priority**: 2

**Dependencies:**
- ultralytics
- segment-anything
- opencv-python
- scikit-image
- insightface
- onnxruntime

**Features:**
- Advanced ControlNet nodes
- Image segmentation
- Face detection and processing
- Object detection
- Image enhancement

**Key Nodes:**
- `ImpactControlNetLoader`
- `ImpactImageBatch`
- `ImpactImageBatchFromList`
- `ImpactSegmentation`
- `ImpactFaceDetector`

### 3. rgthree-comfy

**Purpose**: Enhanced workflow utilities and nodes
**Repository**: https://github.com/rgthree/rgthree-comfy.git
**Priority**: 3

**Features:**
- Workflow utilities
- Enhanced node connections
- Batch processing
- Image manipulation

**Key Nodes:**
- `rgthree.Math`
- `rgthree.Utils`
- `rgthree.Image`
- `rgthree.Batch`

### 4. ComfyUI-Advanced-ControlNet

**Purpose**: Advanced ControlNet implementations
**Repository**: https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet.git
**Priority**: 4

**Dependencies:**
- controlnet-aux
- mediapipe
- transformers

**Features:**
- Advanced ControlNet models
- Multiple ControlNet support
- Enhanced preprocessing
- Better integration

**Key Nodes:**
- `AdvancedControlNetLoader`
- `AdvancedControlNetApply`
- `ControlNetPreprocessor`

### 5. ComfyUI-VideoHelperSuite

**Purpose**: Video processing and generation nodes
**Repository**: https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
**Priority**: 5

**Dependencies:**
- opencv-python
- imageio
- imageio-ffmpeg
- numpy

**Features:**
- Video generation
- Video processing
- Frame extraction
- Video enhancement

**Key Nodes:**
- `VideoCombine`
- `VideoUncombine`
- `VideoFromFrames`
- `FramesFromVideo`

## Configuration

### Custom Nodes Config

The configuration is stored in `/workspace/configs/custom_nodes.json`:

```json
{
  "custom_nodes": [
    {
      "name": "ComfyUI-Manager",
      "description": "Essential node manager for ComfyUI",
      "repository": "https://github.com/ltdrdata/ComfyUI-Manager.git",
      "branch": "main",
      "requirements": [],
      "priority": 1,
      "essential": true
    }
    // ... more nodes
  ],
  "installation_order": [
    "ComfyUI-Manager",
    "ComfyUI-Impact-Pack",
    "rgthree-comfy",
    "ComfyUI-Advanced-ControlNet",
    "ComfyUI-VideoHelperSuite"
  ]
}
```

### Adding Custom Nodes

To add new custom nodes:

1. Edit `/workspace/configs/custom_nodes.json`
2. Add node configuration:
```json
{
  "name": "Your-Custom-Node",
  "description": "Description of your node",
  "repository": "https://github.com/user/repo.git",
  "branch": "main",
  "requirements": ["package1", "package2"],
  "priority": 6,
  "essential": false
}
```
3. Add to installation order
4. Rebuild Docker image or run install script

## Management

### Installation Script

The `install_custom_nodes.sh` script provides:

```bash
# Basic installation
./install_custom_nodes.sh

# Custom configuration
./install_custom_nodes.sh --config /custom/config.json

# Custom ComfyUI path
./install_custom_nodes.sh --comfyui-path /custom/comfyui

# Verbose output
./install_custom_nodes.sh --verbose

# Help
./install_custom_nodes.sh --help
```

### Verification

Check installed nodes:

```bash
# List installed custom nodes
ls -la /workspace/ComfyUI/custom_nodes/

# Check specific node
ls -la /workspace/ComfyUI/custom_nodes/ComfyUI-Manager/

# Verify installation
/workspace/scripts/install_custom_nodes.sh --verbose
```

## Usage Examples

### Basic Workflow with Custom Nodes

```python
# Example workflow using custom nodes
workflow = {
    "1": {
        "class_type": "ImpactControlNetLoader",
        "inputs": {
            "control_net_name": "control_v11p_sd15_canny.pth"
        }
    },
    "2": {
        "class_type": "ImpactImageBatch",
        "inputs": {
            "image": "path/to/image.jpg"
        }
    }
    # ... more nodes
}
```

### Video Generation Workflow

```python
# Video generation using VideoHelperSuite
video_workflow = {
    "1": {
        "class_type": "VideoFromFrames",
        "inputs": {
            "frames": "path/to/frames/",
            "fps": 24
        }
    },
    "2": {
        "class_type": "VideoCombine",
        "inputs": {
            "video": "1",
            "audio": "path/to/audio.wav"
        }
    }
}
```

## Troubleshooting

### Common Issues

1. **Node not found**
   ```bash
   # Check if node is installed
   ls -la /workspace/ComfyUI/custom_nodes/NodeName/
   
   # Reinstall if missing
   /workspace/scripts/install_custom_nodes.sh
   ```

2. **Missing dependencies**
   ```bash
   # Check node requirements
   cat /workspace/ComfyUI/custom_nodes/NodeName/requirements.txt
   
   # Install manually
   pip install missing-package
   ```

3. **Node errors**
   ```bash
   # Check ComfyUI logs
   tail -f /workspace/logs/comfyui_stderr.log
   
   # Enable verbose mode
   export COMFY_VERBOSE=1
   ```

### Debugging

```bash
# Check node installation status
python3 -c "
import json
with open('/workspace/configs/custom_nodes.json') as f:
    config = json.load(f)
    for node in config['custom_nodes']:
        import os
        path = f'/workspace/ComfyUI/custom_nodes/{node[\"name\"]}'
        print(f'{node[\"name\"]}: {\"✅\" if os.path.exists(path) else \"❌\"} {path}')
"

# Test node imports
python3 -c "
import sys
sys.path.append('/workspace/ComfyUI/custom_nodes/ComfyUI-Manager')
try:
    import manager
    print('✅ ComfyUI-Manager imported successfully')
except Exception as e:
    print(f'❌ ComfyUI-Manager import failed: {e}')
"
```

## Performance Impact

### Resource Usage

Custom nodes add minimal overhead:
- **Disk space**: ~500MB total
- **Memory**: ~50MB additional
- **Startup time**: +5-10 seconds

### Optimization

For better performance:

```bash
# Disable unused nodes
# Edit custom_nodes.json and set "essential": false

# Use only required nodes
# Remove unnecessary nodes from installation_order
```

## Updates

### Updating Custom Nodes

```bash
# Update all custom nodes
/workspace/scripts/install_custom_nodes.sh

# Update specific node
cd /workspace/ComfyUI/custom_nodes/NodeName
git pull origin main
```

### Version Management

Custom nodes are pinned to specific commits during Docker build for stability. To update:

1. Modify `custom_nodes.json`
2. Rebuild Docker image
3. Or run install script manually

## Support

For custom node issues:

1. Check the logs: `/workspace/logs/`
2. Verify node installation
3. Check dependencies
4. Test with minimal workflow
5. Check node documentation